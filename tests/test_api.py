"""End-to-end API tests through the FastAPI app."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["LOGOSECO_POLICY_VERSION"] = "v1-test"
os.environ["LOGOSECO_APPROVER_TOKEN"] = "test-approver-token"

from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.approver import plan_sha256  # noqa: E402
from app.governance.signed_approver import SignedApproverClient, SIGNED_FIELDS  # noqa: E402

client = TestClient(main.app)


def _binding(capability, plan):
    return {
        "capability": capability,
        "application": "12d_synergy",
        "plan_sha256": plan_sha256(list(plan)),
        "execution_target": "https://staging.12dsynergy.test/api",
        "session_id": "sess-1",
        "principal_id": "dion",
        "action_id": "act-1",
    }


def _verifier(tmp_path):
    pub = tmp_path / "pub.pem"
    r = client.get("/status")
    pub.write_text(r.json()["public_key_pem"])
    return SignedApproverClient(socket_path=str(tmp_path / "x.sock"),
                                public_key_path=str(pub),
                                used_ledger_path=str(tmp_path / "used.log"))


def test_status_ok():
    r = client.get("/status")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "OK" and body["mode"] == "LIVE_SERVICE"
    assert "BEGIN PUBLIC KEY" in body["public_key_pem"]


def test_govern_read_grants_and_verifies(tmp_path):
    plan = ["query_jobs"]
    r = client.post("/govern", json={"plan": plan, "binding": _binding("read", plan)})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "GRANTED"
    grant = body["grant"]
    assert set(grant) == set(SIGNED_FIELDS) | {"signature"}
    assert _verifier(tmp_path).verify_signature(grant) is True


def test_govern_send_pends():
    plan = ["gmail.send"]
    r = client.post("/govern", json={"plan": plan, "binding": _binding("send", plan)})
    assert r.json()["status"] == "PENDING_HUMAN"


def test_plan_hash_mismatch_rejected():
    body = {"plan": ["query_jobs"], "binding": _binding("read", ["something_else"])}
    r = client.post("/govern", json=body)
    assert r.status_code == 400


def test_human_approval_flow(tmp_path):
    plan = ["gmail.send"]
    r = client.post("/govern", json={"plan": plan, "binding": _binding("send", plan)})
    pending_id = r.json()["pending_id"]
    # unauthorized
    assert client.post(f"/pending/{pending_id}/approve").status_code == 401
    # authorized
    r2 = client.post(f"/pending/{pending_id}/approve",
                     headers={"Authorization": "Bearer test-approver-token"})
    assert r2.status_code == 200
    grant = r2.json()["grant"]
    assert grant["verdict"] == "HUMAN_APPROVED"
    assert _verifier(tmp_path).verify_signature(grant) is True
    # can't approve twice
    assert client.post(f"/pending/{pending_id}/approve",
                       headers={"Authorization": "Bearer test-approver-token"}).status_code == 409


def test_audit_records():
    client.post("/govern", json={"plan": ["query_jobs"], "binding": _binding("read", ["query_jobs"])})
    r = client.get("/audit")
    assert r.status_code == 200
    assert len(r.json()["records"]) >= 1
