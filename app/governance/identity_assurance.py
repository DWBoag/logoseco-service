import hashlib
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class IdentityState(str, Enum):
    UNKNOWN="UNKNOWN"; CLAIMED="CLAIMED"; RECOGNISED="RECOGNISED"; AUTHENTICATED="AUTHENTICATED"
    VERIFIED="VERIFIED"; ELEVATED="ELEVATED"; SUSPICIOUS="SUSPICIOUS"; LOCKED="LOCKED"; REVOKED="REVOKED"

@dataclass
class IdentitySignal:
    source: str
    claim: str
    confidence: float
    observed_at: str
    detail: str = ""

@dataclass
class IdentityAssurance:
    state: IdentityState = IdentityState.UNKNOWN
    subject: str | None = None
    confidence: float = 0.0
    signals: list[IdentitySignal] = field(default_factory=list)
    enrolled_device_fingerprint: str | None = None
    revoked: bool = False

    def claim(self, subject):
        if not isinstance(subject, str) or not subject.strip():
            raise ValueError("claimed subject must be a non-empty string")
        subject = subject.strip()
        # Evidence gathered for one claimed person must never silently carry
        # over to a different claim. Revocation, however, is sticky.
        if self.subject is not None and self.subject != subject and not self.revoked:
            self.signals.clear()
            self.confidence = 0.0
            self.enrolled_device_fingerprint = None
            self.state = IdentityState.UNKNOWN
        self.subject = subject
        if self.revoked:
            self.state = IdentityState.REVOKED
        elif self.state == IdentityState.UNKNOWN:
            self.state = IdentityState.CLAIMED

    def add_signal(self, source, claim, confidence, detail=""):
        if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
            raise ValueError("signal confidence must be between 0 and 1")
        self.signals.append(IdentitySignal(source,claim,confidence,datetime.now(timezone.utc).isoformat(),detail))
        # Signal confidence is not identity assurance. Discovery metadata (even
        # a high-scoring signal) cannot authenticate or verify a human. Those
        # states require a separate, explicitly implemented verification path.
        if self.revoked:
            self.state=IdentityState.REVOKED
        elif confidence >= .45 and self.state in {IdentityState.UNKNOWN, IdentityState.CLAIMED, IdentityState.RECOGNISED}:
            self.state=IdentityState.RECOGNISED
        elif self.state == IdentityState.UNKNOWN:
            self.state=IdentityState.CLAIMED
        self.confidence=max(self.confidence,confidence)

    def enroll_device(self, material):
        self.enrolled_device_fingerprint=hashlib.sha256(material.encode()).hexdigest()

    def revoke(self, reason=""):
        self.revoked=True
        self.state=IdentityState.REVOKED
        self.signals.append(IdentitySignal("revocation","identity revoked",1.0,datetime.now(timezone.utc).isoformat(),reason))

class PersonalDiscoveryEngine:
    def __init__(self, workspace):
        self.workspace=Path(workspace)

    def discover(self, claimed_name, assurance):
        assurance.claim(claimed_name)
        signals=[]
        def add(source,claim,confidence,detail):
            sig=IdentitySignal(source,claim,confidence,datetime.now(timezone.utc).isoformat(),detail)
            signals.append(sig); assurance.add_signal(source,claim,confidence,detail)
        try:
            name=subprocess.check_output(["git","-C",str(self.workspace),"config","--get","user.name"],text=True,stderr=subprocess.DEVNULL,timeout=3).strip()
            email=subprocess.check_output(["git","-C",str(self.workspace),"config","--get","user.email"],text=True,stderr=subprocess.DEVNULL,timeout=3).strip()
            if name or email:
                add("local_git_config",f"Git identity: {name} <{email}>",.65,"Local repository configuration; corroboration only.")
        except Exception: pass
        try:
            login=subprocess.check_output(["gh","api","user","--jq",".login"],text=True,stderr=subprocess.DEVNULL,timeout=8).strip()
            if login:
                add("github_authenticated_session",f"GitHub account: {login}",.80,"Authenticated local GitHub CLI session; corroboration only.")
        except Exception: pass
        if self.workspace.exists():
            add("authorized_local_workspace",f"Padawan workspace exists at {self.workspace}",.55,"Local possession/provenance signal; not identity proof.")
        if not signals:
            assurance.confidence=.10
        return signals

    def report(self, claimed_name, assurance, signals):
        from .desktop_discovery import DesktopCapabilityDiscovery
        capability = DesktopCapabilityDiscovery().discover()
        lines=[
            f"Identity discovery for: {claimed_name}",
            f"State: {assurance.state.value}",
            f"Strongest discovery-signal score (not identity assurance): {assurance.confidence:.2f}",
            "",
            "Identity evidence found:"
        ]
        lines += [f"- {s.source}: {s.claim} (confidence {s.confidence:.2f})" for s in signals] or ["- No corroborating local signals were available."]
        lines += ["", "DISCOVERABLE DESKTOP CAPABILITIES", capability.render(),
                  "", "Boundary: these signals do not independently prove legal identity.",
                  "Identity, authentication, consent and authority remain separate."]
        return "\n".join(lines)
