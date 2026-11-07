import unittest

from app.governance.identity_assurance import IdentityAssurance, IdentityState


class IdentityAssuranceBoundaryTests(unittest.TestCase):
    def test_high_confidence_discovery_signal_does_not_authenticate_or_verify(self):
        assurance = IdentityAssurance()
        assurance.claim("Alice Example")
        assurance.add_signal("public_web_match", "Possible match", 0.99)
        self.assertEqual(assurance.state, IdentityState.RECOGNISED)
        self.assertNotEqual(assurance.state, IdentityState.AUTHENTICATED)
        self.assertNotEqual(assurance.state, IdentityState.VERIFIED)

    def test_switching_claimed_subject_clears_prior_subject_evidence(self):
        assurance = IdentityAssurance()
        assurance.claim("Alice Example")
        assurance.add_signal("local_metadata", "Alice account metadata", 0.80)
        assurance.enroll_device("alice-device-material")
        assurance.claim("Bob Example")
        self.assertEqual(assurance.subject, "Bob Example")
        self.assertEqual(assurance.state, IdentityState.CLAIMED)
        self.assertEqual(assurance.signals, [])
        self.assertEqual(assurance.confidence, 0.0)
        self.assertIsNone(assurance.enrolled_device_fingerprint)

    def test_revocation_survives_new_claim_and_new_signals(self):
        assurance = IdentityAssurance()
        assurance.claim("Alice Example")
        assurance.revoke("operator revoked identity")
        assurance.claim("Bob Example")
        assurance.add_signal("trusted_looking_source", "New match", 1.0)
        self.assertEqual(assurance.state, IdentityState.REVOKED)
        self.assertTrue(assurance.revoked)

    def test_invalid_signal_confidence_is_rejected(self):
        assurance = IdentityAssurance()
        assurance.claim("Alice Example")
        for value in (-0.1, 1.1, float("nan"), "0.9"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                assurance.add_signal("source", "claim", value)

    def test_empty_claim_is_rejected(self):
        with self.assertRaises(ValueError):
            IdentityAssurance().claim("  ")


if __name__ == "__main__":
    unittest.main()
