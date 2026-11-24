"""Rebuild a synthetic subscription projection from late and duplicate provider events."""

import json
import sqlite3
from contextlib import closing

TRANSITIONS = {
    ("uninitialized", "created"): "trial",
    ("trial", "activated"): "active",
    ("active", "payment_failed"): "past_due",
    ("past_due", "payment_recovered"): "active",
    ("active", "cancelled"): "cancelled",
    ("past_due", "cancelled"): "cancelled",
    ("trial", "cancelled"): "cancelled",
}


def prepare(db):
    db.executescript("""CREATE TABLE events (provider_id TEXT PRIMARY KEY, subscription TEXT, sequence INTEGER,
      kind TEXT, cents INTEGER, UNIQUE(subscription,sequence)); CREATE TABLE projections (
      subscription TEXT PRIMARY KEY, last_sequence INTEGER, state TEXT, collected INTEGER, unresolved TEXT);""")


def ingest(db, provider_id, subscription, sequence, kind, cents=0):
    if (
        not provider_id
        or not subscription
        or type(sequence) is not int
        or sequence < 1
        or type(cents) is not int
        or cents < 0
    ):
        raise ValueError("Invalid event identity, sequence, or amount")
    if kind not in {event for _, event in TRANSITIONS} or (
        cents and kind not in ("activated", "payment_recovered")
    ):
        raise ValueError("Unsupported event type or amount")
    event = (provider_id, subscription, sequence, kind, cents)
    with db:
        db.execute("BEGIN IMMEDIATE")
        prior = db.execute("SELECT * FROM events WHERE provider_id=?", (provider_id,)).fetchone()
        if prior:
            if prior != event:
                raise ValueError("Provider event ID has a different payload")
            return {"duplicate": True, **snapshot(db, subscription)}
        db.execute("INSERT INTO events VALUES (?,?,?,?,?)", event)
        contiguous, state, total, blocked = 0, "uninitialized", 0, None
        for number, label, value in db.execute(
            "SELECT sequence,kind,cents FROM events WHERE subscription=? ORDER BY sequence",
            (subscription,),
        ):
            if number != contiguous + 1 or (state, label) not in TRANSITIONS:
                blocked = (
                    f"sequence {number}: expected {contiguous + 1}"
                    if number != contiguous + 1
                    else f"sequence {number}: illegal transition"
                )
                break
            state = TRANSITIONS[state, label]
            contiguous = number
            total += value
        db.execute(
            """INSERT INTO projections VALUES (?,?,?,?,?) ON CONFLICT(subscription) DO UPDATE SET
          last_sequence=excluded.last_sequence,state=excluded.state,collected=excluded.collected,unresolved=excluded.unresolved""",
            (subscription, contiguous, state, total, blocked),
        )
        return {"duplicate": False, **snapshot(db, subscription)}


def snapshot(db, subscription):
    result = db.execute(
        "SELECT last_sequence,state,collected,unresolved FROM projections WHERE subscription=?",
        (subscription,),
    ).fetchone()
    return dict(zip(("through", "state", "collected_cents", "unresolved"), result, strict=True))


def demo():
    with closing(sqlite3.connect(":memory:")) as db:
        prepare(db)
        steps = [
            ingest(db, *event)
            for event in (
                ("e1", "demo", 1, "created"),
                ("e3", "demo", 3, "payment_failed"),
                ("e2", "demo", 2, "activated", 5900),
                ("e4", "demo", 4, "payment_recovered", 5900),
                ("e4", "demo", 4, "payment_recovered", 5900),
            )
        ]
        return {
            "projection_steps": steps,
            "provider_events": db.execute("SELECT count(*) FROM events").fetchone()[0],
        }


if __name__ == "__main__":
    print(json.dumps(demo(), indent=2))
