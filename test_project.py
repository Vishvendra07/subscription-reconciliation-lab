import sqlite3
import unittest
from project import demo, ingest, prepare


class SubscriptionTests(unittest.TestCase):
    def test_gap_closure_and_duplicate_amount(self):
        result = demo()
        _, gap, resolved, recovered, duplicate = result["projection_steps"]
        self.assertIn("expected 2", gap["unresolved"])
        self.assertEqual(resolved["state"], "past_due")
        self.assertEqual(recovered["collected_cents"], 11800)
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["collected_cents"], 11800)
        self.assertEqual(result["provider_events"], 4)

    def test_changed_provider_id_preserves_original_event(self):
        with sqlite3.connect(":memory:") as db:
            prepare(db)
            ingest(db, "e1", "s", 1, "created")
            with self.assertRaises(ValueError):
                ingest(db, "e1", "s", 2, "activated", 10)
            self.assertEqual(
                db.execute("SELECT sequence,kind FROM events").fetchall(), [(1, "created")]
            )
