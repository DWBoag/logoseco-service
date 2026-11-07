import unittest

from app.governance.governance import ConstitutionalGate, GovernanceVerdict


class ConstitutionalGateTests(unittest.TestCase):
    def setUp(self):
        self.gate = ConstitutionalGate()

    def test_bounded_action_with_complete_context_is_allowed(self):
        result = self.gate.assess(
            capability="filesystem.write",
            plan=[{"op": "write_text"}],
            context_snapshot="WHO/WHAT/WHERE/WHEN/WHY/HOW captured",
        )
        self.assertEqual(result.verdict, GovernanceVerdict.ALLOW)

    def test_bounded_action_without_context_is_limited_not_authority_free(self):
        result = self.gate.assess(
            capability="filesystem.write",
            plan=[{"op": "write_text"}],
        )
        self.assertEqual(result.verdict, GovernanceVerdict.ALLOW_WITH_LIMITS)
        self.assertTrue(result.limits["context_required_for_future_escalation"])

    def test_consequential_external_capability_requires_human(self):
        result = self.gate.assess(
            capability="communicate",
            plan=[{"op": "send_message"}],
            context_snapshot="complete",
        )
        self.assertEqual(result.verdict, GovernanceVerdict.REQUIRE_HUMAN_APPROVAL)

    def test_namespaced_communicate_capability_requires_human(self):
        result = self.gate.assess(
            capability="communication.send",
            plan=[{"op": "send_message"}],
            context_snapshot="complete",
        )
        self.assertEqual(result.verdict, GovernanceVerdict.REQUIRE_HUMAN_APPROVAL)

    def test_capability_matching_is_case_insensitive(self):
        result = self.gate.assess(
            capability="COMMUNICATION.SEND",
            plan=[{"op": "send_message"}],
            context_snapshot="complete",
        )
        self.assertEqual(result.verdict, GovernanceVerdict.REQUIRE_HUMAN_APPROVAL)

    def test_empty_plan_is_blocked(self):
        result = self.gate.assess(capability="filesystem.write", plan=[])
        self.assertEqual(result.verdict, GovernanceVerdict.BLOCK)

    def test_consequential_plan_cannot_hide_under_benign_capability(self):
        for step in (
            {"op": "purchase", "item": "license"},
            {"operation": "send_message", "to": "external"},
            {"nested": {"action": "delete", "target": "record"}},
            {"op": "agent.destroy"},
        ):
            with self.subTest(step=step):
                result = self.gate.assess(
                    capability="filesystem.write",
                    plan=[step],
                    context_snapshot="complete",
                )
                self.assertEqual(
                    result.verdict, GovernanceVerdict.REQUIRE_HUMAN_APPROVAL
                )

    def test_sensitive_capabilities_cannot_bypass_gate_with_namespace_suffix(self):
        for capability in (
            "agent.destroy-agent.v2",
            "workflow.create_agent",
            "finance.purchase.card",
            "communications.send-email",
            "records.publish.report",
            "approval.review",
            "agent.delete",
            "authority.revoke",
            "account.transfer",
            "agent.terminate",
        ):
            with self.subTest(capability=capability):
                result = self.gate.assess(
                    capability=capability,
                    plan=[{"op": "execute"}],
                    context_snapshot="complete",
                )
                self.assertEqual(result.verdict, GovernanceVerdict.REQUIRE_HUMAN_APPROVAL)


if __name__ == "__main__":
    unittest.main()
