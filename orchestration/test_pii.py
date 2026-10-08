import unittest

from .pii import PIIProtector


class PIIProtectorTests(unittest.TestCase):
    def test_masks_and_restores_common_customer_identifiers(self):
        protector = PIIProtector()
        source = "CUST-10002 can be reached at alex@example.com or +1 (512) 555-0100."

        protected = protector.protect(source)

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