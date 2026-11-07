import unittest

from app.governance.governance import GovernanceVerdict
from app.governance.logoseco_governance import LogosecoGovernanceSubstrate


class LogosecoGovernanceSubstrateTests(unittest.TestCase):
    def test_local_mode_is_explicit_and_does_not_claim_remote_connection(self):
        substrate = LogosecoGovernanceSubstrate()
        self.assertEqual(substrate.mode, "LOCAL_POLICY_KERNEL")
        self.assertIs(substrate.remote_service_connected, False)

    def test_every_assessment_is_recorded_with_mode_and_decision(self):
        substrate = LogosecoGovernanceSubstrate()
        assessment = substrate.assess(
            capability="demo.execute",
            plan=[{"op": "demo"}],
            context_snapshot="complete test context",
        )
        self.assertEqual(assessment.verdict, GovernanceVerdict.ALLOW)
        self.assertEqual(len(substrate.decisions), 1)
        record = substrate.decisions[0]
        self.assertEqual(record.assessment, assessment)
        self.assertEqual(record.mode, "LOCAL_POLICY_KERNEL")
        self.assertFalse(record.remote_service_connected)
        self.assertTrue(record.decision_id.startswith("lgd-"))
        self.assertTrue(record.decided_at)

    def test_consequential_action_is_not_overridden_by_facade(self):
        substrate = LogosecoGovernanceSubstrate()
        assessment = substrate.assess(
            capability="demo.execute",
            plan=[{"op": "send", "message": "external"}],
            context_snapshot="complete test context",
        )
        self.assertEqual(assessment.verdict, GovernanceVerdict.REQUIRE_HUMAN_APPROVAL)


if __name__ == "__main__":
    unittest.main()
