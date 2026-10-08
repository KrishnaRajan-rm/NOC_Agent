import unittest

from .protector import PIIProtector


class PIIProtectorTests(unittest.TestCase):
    def test_masks_customer_identifiers_but_keeps_tower_context(self):
        protector = PIIProtector()
        source = (
            "Diagnose tower TX-512 at Austin Riverside for CUST-10002, "
            "alex@example.com, or +1 (512) 555-0100."
        )

        protected = protector.protect(source)

        self.assertIn("TX-512", protected)
        self.assertIn("Austin Riverside", protected)
        self.assertNotIn("CUST-10002", protected)
        self.assertNotIn("alex@example.com", protected)
        self.assertNotIn("555-0100", protected)
        self.assertEqual(protector.restore(protected), source)

    def test_reuses_tokens_for_repeated_values(self):
        protector = PIIProtector()

        protected = protector.protect("CUST-10002 contacted CUST-10002.")

        self.assertEqual(protected.count("<PII_CUSTOMER_ID_1>"), 2)


if __name__ == "__main__":
    unittest.main()