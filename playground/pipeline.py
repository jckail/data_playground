"""Deduplicate, validate, quarantine, and aggregate reproducible event streams."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping
from . import ENGINE_VERSION, SCHEMA_VERSION
from .analytics import aggregate
from .config import SimulationConfig
from .simulation import CHANNELS, EVENT_TYPES, PLANS, START_DATE, generate_events

FIELDS = {"event_id", "occurred_at", "user_id", "event_type", "amount_cents", "channel", "plan"}


def validate_events(raw, config):
    """Return accepted events, bounded quarantine, stages, quality reports.

    Invalid records never mutate customer lifecycle state. Deduplication uses
    first occurrence; accepted records are ordered by UTC event time then ID.
    """
    quarantined = []
    stages = []
    quality = []

    def reject(event, reason):
        sample = {"event_id": str(event.get("event_id", "unknown"))[:100],
                  "event_type": str(event.get("event_type", "unknown"))[:100], "reason": reason}
        if len(quarantined) < 50:
            quarantined.append(sample)
        elif not any(item["reason"] == reason for item in quarantined):
            # Preserve failure diversity even when duplicates fill the sample early.
            common = Counter(item["reason"] for item in quarantined).most_common(1)[0][0]
            replace = next(i for i in range(len(quarantined) - 1, -1, -1) if quarantined[i]["reason"] == common)
            quarantined[replace] = sample

    def record(stage_id, name, checked, failed, description):
        stages.append(dict(id=stage_id, name=name, input_count=checked, output_count=checked - failed,
                           rejected_count=failed, description=description))
        quality.append(dict(id=stage_id, name=name, status="warn" if failed else "pass", checked=checked,
                            failed=failed, description=description))

    unique = []
    seen = set()
    for event in raw:
        if not isinstance(event, dict):
            event = {}
        event_id = event.get("event_id")
        if isinstance(event_id, str) and event_id in seen:
            reject(event, "duplicate event_id")
        else:
            if isinstance(event_id, str):
                seen.add(event_id)
            unique.append(event)
    record("dedup", "Deduplicate", len(raw), len(raw) - len(unique), "First occurrence wins by event_id.")
    valid = []
    start = datetime.combine(START_DATE, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=config.days)
    for event in unique:
        reason = None
        if set(event) != FIELDS:
            reason = "invalid event fields"
        elif any(not isinstance(event[k], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", event[k]) for k in ("event_id", "user_id")):
            reason = "invalid event or user identifier"
        elif any(not isinstance(event[k], str) for k in ("event_type", "channel", "plan")) or event["event_type"] not in EVENT_TYPES or event["channel"] not in CHANNELS or event["plan"] not in PLANS:
            reason = "invalid event type, channel, or plan"
        elif type(event["amount_cents"]) is not int or not 0 <= event["amount_cents"] <= 1000000:
            reason = "amount_cents must be bounded nonnegative integer cents"
        elif (event["event_type"] == "payment" and event["amount_cents"] != PLANS[event["plan"]]) or (event["event_type"] != "payment" and event["amount_cents"] != 0):
            reason = "amount does not match event and subscription plan"
        else:
            try:
                stamp = event["occurred_at"]
                if not isinstance(stamp, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stamp):
                    raise ValueError("timestamp")
                instant = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if not start <= instant < end:
                    raise ValueError("window")
            except (ValueError, TypeError):
                reason = "invalid UTC timestamp or outside observation window"
        if reason:
            reject(event, reason)
        else:
            valid.append(event)
    record("schema", "Validate schema", len(unique), len(unique) - len(valid), "Check fields, identifiers, UTC dates, enums and integer payment amounts.")
    accepted = []
    states = {}
    relationship_failed = 0
    lifecycle_failed = 0
    for event in sorted(valid, key=lambda e: (e["occurred_at"], e["event_id"])):
        uid, kind = event["user_id"], event["event_type"]
        state = states.get(uid)
        if kind != "signup" and state is None:
            reject(event, "unknown user: signup must precede downstream events")
            relationship_failed += 1
            continue
        reason = None
        if kind == "signup":
            if state is not None:
                reason = "duplicate signup for user"
        elif event["channel"] != state["channel"] or event["plan"] != state["plan"]:
            reason = "user channel or plan changed"
        elif event["occurred_at"] <= state["last"]:
            reason = "lifecycle events must occur at strictly increasing times"
        elif state["stage"] == "churn":
            reason = "event after churn"
        elif kind == "activation" and state["stage"] != "signup":
            reason = "activation requires an unactivated signup"
        elif kind == "payment" and state["stage"] not in ("activation", "payment"):
            reason = "payment requires activation"
        elif kind == "churn" and state["stage"] != "payment":
            reason = "churn requires a paying customer"
        if reason:
            reject(event, reason)
            lifecycle_failed += 1
            continue
        states[uid] = dict(stage=kind, channel=event["channel"], plan=event["plan"], last=event["occurred_at"])
        accepted.append(event)
    record("relationships", "Check relationships", len(valid), relationship_failed, "Downstream events require a preceding accepted signup.")
    record("lifecycle", "Check lifecycle", len(valid) - relationship_failed, lifecycle_failed, "Enforce signup → activation → payments → churn with increasing timestamps and stable user attributes.")
    stages.append(dict(id="warehouse", name="SQLite warehouse", input_count=len(accepted), output_count=len(accepted), rejected_count=0,
                       description="Load accepted events into an in-memory SQLite table and execute the lineage queries."))
    return accepted, quarantined, stages, quality


def run_simulation(config, scenario=None):
    if isinstance(config, Mapping):
        config = SimulationConfig(**config)
    if not isinstance(config, SimulationConfig):
        raise TypeError("config must be SimulationConfig or a mapping")
    if scenario is None:
        scenario = dict(id="custom", name="Custom simulation", description="A seeded synthetic commerce simulation.")
    if not isinstance(scenario, Mapping) or set(scenario) != {"id", "name", "description"}:
        raise ValueError("scenario requires id, name and description")
    scenario = dict(scenario)
    if any(not isinstance(value, str) or not value.strip() for value in scenario.values()):
        raise ValueError("scenario values must be nonempty strings")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", scenario["id"]) or len(scenario["name"]) > 100 or len(scenario["description"]) > 1000:
        raise ValueError("invalid scenario identifier or text length")
    identity = dict(config=config.to_dict(), scenario=scenario, engine_version=ENGINE_VERSION, schema_version=SCHEMA_VERSION)
    run_id = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]
    raw = generate_events(config)
    accepted, quarantined, pipeline, quality = validate_events(raw, config)
    summary, daily, funnel, cohorts, lineage = aggregate(accepted, config, len(raw))
    # Spread samples across the observation window, retaining each observed type.
    sample_indexes = set()
    if accepted:
        for kind in EVENT_TYPES:
            first = next((i for i, event in enumerate(accepted) if event["event_type"] == kind), None)
            if first is not None:
                sample_indexes.add(first)
        slots = 100 - len(sample_indexes)
        sample_indexes.update(round(i * (len(accepted) - 1) / max(slots - 1, 1)) for i in range(slots))
    sample = [accepted[i] for i in sorted(sample_indexes)]
    return dict(id=f"run-{run_id}", scenario=scenario, config=config.to_dict(), summary=summary,
                daily=daily, funnel=funnel, cohorts=cohorts, pipeline=pipeline, quality=quality,
                events=sample, quarantined=quarantined, lineage=lineage)
