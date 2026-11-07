import unittest
from unittest.mock import Mock

from app.governance.signed_approver import SignedApproverClient


class SignedApproverHealthTests(unittest.TestCase):
    def client_with_reply(self, reply):
        client = object.__new__(SignedApproverClient)
        client._call = Mock(return_value=reply)
        return client

    def test_healthy_requires_policy_integrity_and_audit_metadata(self):
        client = self.client_with_reply({
            "status": "OK",
            "policy_intact": True,
            "policy_version": "a" * 64,
            "log_records": 4,
        })
        self.assertTrue(client.healthy())
        client._call.assert_called_once_with({"op": "health"})

    def test_policy_integrity_failure_is_not_healthy(self):
        client = self.client_with_reply({
            "status": "OK",
            "policy_intact": False,
            "policy_version": "a" * 64,
            "log_records": 4,
        })
        self.assertFalse(client.healthy())

    def test_missing_policy_version_is_not_healthy(self):
        client = self.client_with_reply({
            "status": "OK", "policy_intact": True, "log_records": 4,
        })
        self.assertFalse(client.healthy())

    def test_invalid_audit_record_count_is_not_healthy(self):
        for count in (True, -1, "4", None):
            with self.subTest(count=count):
                client = self.client_with_reply({
                    "status": "OK",
                    "policy_intact": True,
                    "policy_version": "a" * 64,
                    "log_records": count,
                })
                self.assertFalse(client.healthy())

    def test_non_ok_status_is_not_healthy(self):
        client = self.client_with_reply({
            "status": "BLOCKED",
            "policy_intact": True,
            "policy_version": "a" * 64,
            "log_records": 4,
        })
        self.assertFalse(client.healthy())

    def test_transport_failure_is_not_healthy(self):
        client = object.__new__(SignedApproverClient)
        client._call = Mock(side_effect=OSError("unavailable"))
        self.assertFalse(client.healthy())

    def test_malformed_reply_is_not_healthy(self):
        client = object.__new__(SignedApproverClient)
        client._call = Mock(side_effect=ValueError("malformed response"))
        self.assertFalse(client.healthy())


if __name__ == "__main__":
    unittest.main()
