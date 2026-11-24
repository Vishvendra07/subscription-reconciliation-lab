# Subscription Reconciliation Lab

Show what happens when a synthetic billing event arrives before its predecessor and when a processed event is replayed.

[Source](project.py) · [Demo evidence](evidence/demo.json) · [Verification](evidence/checks.json)

## Run locally

Requires Python 3.11+.

```sh
python project.py
python -m unittest discover -v
```

## Engineering decision

Build a projection only through the highest contiguous valid event. Use provider identity and sequence uniqueness to preserve an auditable history.

A single authored lifecycle and fixed currency. No payment provider charges or ledger handling.



[Technology or project reference](https://docs.python.org/3/library/sqlite3.html)
