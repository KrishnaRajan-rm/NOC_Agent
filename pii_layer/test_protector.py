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
        self.assertIn("<PII_ENCRYPTED_", protected)
        self.assertTrue(protector._encrypted_by_token)
        self.assertEqual(protector.restore(protected), source)

    def test_reuses_tokens_for_repeated_values(self):
        protector = PIIProtector()

        protected = protector.protect("CUST-10002 contacted CUST-10002.")

        self.assertEqual(protected.count("<PII_ENCRYPTED_CUSTOMER_ID_1>"), 2)

    def test_audit_summary_and_has_protected_pii(self):
        protector = PIIProtector()
        self.assertFalse(protector.has_protected_pii)
        self.assertEqual(protector.audit_summary(), "none detected")

        source = "Contact CUST-10002 at support@prodapt.com or +1 512-555-0100."
        protected = protector.protect(source)

        self.assertTrue(protector.has_protected_pii)
        self.assertEqual(len(protector.tokens), 3)
        summary = protector.audit_summary(source)
        self.assertIn("CUSTOMER_ID x1", summary)
        self.assertIn("EMAIL x1", summary)
        self.assertIn("PHONE x1", summary)
        self.assertEqual(protector.restore(protected), source)

    def test_non_pii_telemetry_unchanged(self):
        protector = PIIProtector()
        telemetry = "Tower FL-090 in Miami reported 100% packet loss on 5G carrier."
        protected = protector.protect(telemetry)

        self.assertEqual(protected, telemetry)
        self.assertFalse(protector.has_protected_pii)
        self.assertEqual(protector.audit_summary(telemetry), "none detected")


if __name__ == "__main__":
    unittest.main()