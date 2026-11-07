"""Core Stage-1 tests: decision orchestration + grant signing, byte-compatible
with the existing client verifier (app/governance/signed_approver.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.approver import Approver, plan_sha256, ApproverKeyError
from app.decision import decide
from app.floor import GovernanceVector
from app.governance.signed_approver import SignedApproverClient, SIGNED_FIELDS

import pytest


def _binding(capability="read", plan=("query_jobs",)):
    return {
        "capability": capability,
        "application": "12d_synergy",
        "plan_sha256": plan_sha256(list(plan)),
        "execution_target": "https://example.12dsynergy.test/api",
        "session_id": "sess-1",
        "principal_id": "dion",
        "action_id": "act-1",
    }


def _client(tmp_path, approver):
    pub = tmp_path / "pub.pem"
    pub.write_bytes(approver.public_key_pem())
    # socket_path is unused for signature verification
    return SignedApproverClient(
        socket_path=str(tmp_path / "unused.sock"),
        public_key_path=str(pub),
        used_ledger_path=str(tmp_path / "used.log"),
    )


def test_grant_roundtrip_verifies(tmp_path):
    ap = Approver.generate(policy_version="v1-test")
    d = decide(capability="read", plan=["query_jobs"])
    assert d.outcome == "GRANT", d
    grant = ap.mint_grant(verdict=d.grant_verdict, limits=d.limits,
                          binding=_binding("read"), approved_by="logoseco:v1-test")
    client = _client(tmp_path, ap)
    assert set(grant) == set(SIGNED_FIELDS) | {"signature"}
    assert client.verify_signature(grant) is True


def test_tampered_grant_rejected(tmp_path):
    ap = Approver.generate(policy_version="v1-test")
    grant = ap.mint_grant(verdict="ALLOW", limits={}, binding=_binding("read"),
                          approved_by="logoseco:v1-test")
    grant["capability"] = "send"  # tamper a bound field
    client = _client(tmp_path, ap)
    assert client.verify_signature(grant) is False


def test_wrong_key_rejected(tmp_path):
    ap = Approver.generate(policy_version="v1-test")
    other = Approver.generate(policy_version="v1-test")
    grant = ap.mint_grant(verdict="ALLOW", limits={}, binding=_binding("read"),
                          approved_by="logoseco:v1-test")
    client = _client(tmp_path, other)  # verifier has a different public key
    assert client.verify_signature(grant) is False


def test_human_capability_does_not_grant():
    d = decide(capability="send", plan=["gmail.send"])
    assert d.outcome == "PENDING_HUMAN"
    assert d.grant_verdict is None


def test_floor_failure_forces_human():
    # gate would allow a read, but a weak floor dimension must escalate it
    weak = GovernanceVector(honesty=0.95, fairness=0.95, consistency=0.95,
                            learning=0.95, impact=0.20)
    d = decide(capability="read", plan=["query_jobs"], governance_vector=weak)
    assert d.floor_certified is False
    assert d.outcome == "PENDING_HUMAN", d


def test_floor_pass_allows():
    strong = GovernanceVector(honesty=0.95, fairness=0.95, consistency=0.95,
                              learning=0.95, impact=0.95)
    d = decide(capability="read", plan=["query_jobs"], governance_vector=strong)
    assert d.floor_certified is True
    assert d.outcome == "GRANT"


def test_non_executable_verdict_never_minted():
    ap = Approver.generate(policy_version="v1-test")
    with pytest.raises(ApproverKeyError):
        ap.mint_grant(verdict="BLOCK", limits={}, binding=_binding(),
                      approved_by="x")
