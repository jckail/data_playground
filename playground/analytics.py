"""SQLite is the sole aggregation engine; SQL is included as public lineage."""
import sqlite3
from datetime import date, timedelta
from .simulation import START_DATE

SUMMARY_SQL = """SELECT
 COUNT(DISTINCT CASE WHEN event_type='signup' THEN user_id END) AS signups,
 COUNT(DISTINCT CASE WHEN event_type='activation' THEN user_id END) AS activated_users,
 COUNT(DISTINCT CASE WHEN event_type='payment' THEN user_id END) AS paying_users,
 COUNT(DISTINCT CASE WHEN event_type='churn' THEN user_id END) AS churned_users,
 COALESCE(SUM(CASE WHEN event_type='payment' THEN amount_cents ELSE 0 END),0) AS revenue_cents
FROM events"""
DAILY_SQL = """SELECT substr(occurred_at,1,10) AS date,
 SUM(event_type='signup') AS signups, SUM(event_type='activation') AS activations,
 SUM(event_type='payment') AS payments, SUM(event_type='churn') AS churns,
 SUM(CASE WHEN event_type='payment' THEN amount_cents ELSE 0 END) AS revenue_cents
FROM events GROUP BY date ORDER BY date"""
BALANCE_SQL = """SELECT COUNT(DISTINCT p.user_id) FROM events p
WHERE p.event_type='payment' AND substr(p.occurred_at,1,10)<=?
AND NOT EXISTS (SELECT 1 FROM events c WHERE c.user_id=p.user_id
AND c.event_type='churn' AND substr(c.occurred_at,1,10)<=?)"""
CUSTOMERS_SQL = """CREATE TEMP TABLE customers AS
 SELECT user_id, MIN(CASE WHEN event_type='payment' THEN substr(occurred_at,1,10) END) AS first_payment,
 MIN(CASE WHEN event_type='churn' THEN substr(occurred_at,1,10) END) AS churn_date
 FROM events GROUP BY user_id"""
COHORT_SQL = """SELECT first_payment AS cohort, COUNT(*) AS size FROM customers
WHERE first_payment IS NOT NULL GROUP BY first_payment ORDER BY first_payment"""
RETENTION_SQL = """SELECT COUNT(*) FROM customers WHERE first_payment=?
AND (churn_date IS NULL OR churn_date>?)"""


def aggregate(events, config, raw_count):
    with sqlite3.connect(":memory:") as db:
        db.row_factory = sqlite3.Row
        db.execute("CREATE TABLE events(event_id TEXT PRIMARY KEY, occurred_at TEXT, user_id TEXT, event_type TEXT, amount_cents INTEGER, channel TEXT, plan TEXT)")
        db.executemany("INSERT INTO events VALUES (:event_id,:occurred_at,:user_id,:event_type,:amount_cents,:channel,:plan)", events)
        db.execute("CREATE INDEX user_events ON events(user_id,event_type)")
        summary = dict(db.execute(SUMMARY_SQL).fetchone())
        churned = summary.pop("churned_users")
        summary.update(active_customers=summary["paying_users"] - churned,
                       conversion_rate=summary["paying_users"] / summary["signups"] if summary["signups"] else 0,
                       churn_rate=churned / summary["paying_users"] if summary["paying_users"] else 0,
                       quality_pass_rate=len(events) / raw_count if raw_count else 1)
        grouped = {row["date"]: dict(row) for row in db.execute(DAILY_SQL)}
        daily = []
        for offset in range(config.days):
            day = (START_DATE + timedelta(days=offset)).isoformat()
            row = grouped.get(day, dict(date=day, signups=0, activations=0, payments=0, churns=0, revenue_cents=0))
            row["active_customers"] = db.execute(BALANCE_SQL, (day, day)).fetchone()[0]
            daily.append(row)
        funnel = [{"stage": name, "users": summary[key], "rate": summary[key] / summary["signups"] if summary["signups"] else 0}
                  for name, key in (("Signup", "signups"), ("Activation", "activated_users"), ("Payment", "paying_users"))]
        db.execute(CUSTOMERS_SQL)
        db.execute("CREATE INDEX customer_cohort ON customers(first_payment)")
        cohorts = []
        end = START_DATE + timedelta(days=config.days - 1)
        for cohort in db.execute(COHORT_SQL).fetchall():
            start = date.fromisoformat(cohort["cohort"])
            retention = []
            for week in range(13):
                observed = start + timedelta(days=week * 7)
                retention.append(None if observed > end else db.execute(RETENTION_SQL, (start.isoformat(), observed.isoformat())).fetchone()[0] / cohort["size"])
            cohorts.append(dict(cohort=cohort["cohort"], size=cohort["size"], retention=retention))
    lineage = [dict(metric=metric, definition=definition, source="validated SQLite events and derived customers", sql=sql)
               for metric, definition, sql in (
                   ("Summary", "Distinct lifecycle users; revenue is collected subscription payments in integer cents, not MRR. Conversion divides payers by signups; cumulative churn divides churned users by payers.", SUMMARY_SQL),
                   ("Daily activity", "Accepted events grouped by UTC date; recurring payments count as payment events.", DAILY_SQL),
                   ("Active customers", "Ever-paying users with no churn by the selected date (two date parameters).", BALANCE_SQL),
                   ("Customer lifecycle", "Materialize first payment and churn dates once from accepted events.", CUSTOMERS_SQL),
                   ("Cohort size", "Customers grouped by date of first payment.", COHORT_SQL),
                   ("Cohort retention", "Fraction of a first-payment cohort still active at 0,7,...,84 days; future observations are null (cohort and observation date parameters).", RETENTION_SQL))]
    return summary, daily, funnel, cohorts, lineage
