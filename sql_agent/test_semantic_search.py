import sqlite3
import unittest

from .semantic_search import (
    DATABASE_PATH,
    _query_critical_outages,
    _query_latest_packet_loss,
    ask_sql,
)


class SemanticSqlDatabaseTests(unittest.TestCase):
    def test_critical_outage_leader(self):
        self.assertEqual(_query_critical_outages(), ("Midwest", 6))

    def test_latest_packet_loss_ranking(self):
        rows = _query_latest_packet_loss()
        self.assertEqual([row[0] for row in rows], ["FL-090", "TX-208", "IL-221"])
        self.assertEqual([row[3] for row in rows], [100.0, 8.6, 5.4])

    def test_regional_tower_count(self):
        self.assertEqual(
            ask_sql("How many towers are there in Midwest?"),
            "There are 3 towers in the Midwest region.",
        )

    def test_database_contains_expected_tables(self):
        with sqlite3.connect(DATABASE_PATH) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertIn("network_outages", tables)
        self.assertIn("tower_performance", tables)


if __name__ == "__main__":
    unittest.main()