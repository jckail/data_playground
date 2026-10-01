"""Generate causal subscription lifecycles and deliberate corruptions."""
from datetime import date, timedelta
from random import Random

START_DATE = date(2025, 1, 1)
CHANNELS = ("organic", "paid", "referral")
PLANS = {"starter": 1900, "growth": 4900}
EVENT_TYPES = ("signup", "activation", "payment", "churn")


def generate_events(config):
    rng = Random(config.seed)
    events = []
    customers = {}

    def emit(day, uid, kind, channel, plan, amount=0):
        # A fixed daily slot orders all signup/activation/payment/churn events.
        slots = {"signup": "09", "activation": "10", "payment": "11", "churn": "12"}
        events.append({"event_id": f"e-{len(events) + 1:07d}",
                       "occurred_at": f"{day.isoformat()}T{slots[kind]}:00:00Z",
                       "user_id": uid, "event_type": kind, "amount_cents": amount,
                       "channel": channel, "plan": plan})

    for offset in range(config.days):
        day = START_DATE + timedelta(days=offset)
        for uid, state in list(customers.items()):
            born, channel, plan = state
            if rng.random() < config.churn_rate:
                emit(day, uid, "churn", channel, plan)
                del customers[uid]
            elif (offset - born) % 30 == 0:
                emit(day, uid, "payment", channel, plan, PLANS[plan])
        for number in range(config.daily_signups):
            uid = f"u-{offset * config.daily_signups + number + 1:06d}"
            channel = rng.choice(CHANNELS)
            plan = rng.choice(tuple(PLANS))
            emit(day, uid, "signup", channel, plan)
            if rng.random() < config.activation_rate:
                emit(day, uid, "activation", channel, plan)
                if rng.random() < config.payment_rate:
                    emit(day, uid, "payment", channel, plan, PLANS[plan])
                    customers[uid] = (offset, channel, plan)
    # Independent RNG keeps valid business outcomes identical across quality settings.
    noise = Random(config.seed ^ 0x514A)
    raw = []
    for event in events:
        raw.append(event)
        if noise.random() < config.duplicate_rate:
            raw.append(dict(event))
        if noise.random() < config.invalid_rate:
            bad = dict(event, event_id=f"bad-{event['event_id']}")
            if noise.random() < 0.5:
                bad["amount_cents"] = -100
            else:
                bad.update(user_id="missing-user", event_type="activation", amount_cents=0)
            raw.append(bad)
    return sorted(raw, key=lambda e: (e["occurred_at"], e["event_id"]))
