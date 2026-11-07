# LOGOSECO Service

The standalone **governance authority** for the LPH platform. It is deliberately a
*separate service* from Horus/Padawan: authority must not run inside the intelligence it
governs. Horus asks this service to govern a capability; the service decides and, only for
executable outcomes, returns an **Ed25519-signed grant**. The private signing key lives
only here.

**Status:** Stage 1 (freeze 2026-11-07). Core decision + signed-grant minting + HTTP API,
with an in-memory store. Supabase store, deployment, and the Horus-side adapter follow.

## The three-layer decision

A `/govern` request passes all three; the binding result is the **most restrictive**, and
no layer can be compensated by another.

1. **Deterministic gate** — `ConstitutionalGate` (reused from the tested `app/core` kernel).
   Verdicts `ALLOW / ALLOW_WITH_LIMITS / REQUIRE_HUMAN_APPROVAL / BLOCK`.
2. **Governance floor** — the `governance-floor-standard` (harmonic-mean blend + hard
   per-dimension floor). One weak dimension voids certification regardless of the others —
   and a floor failure cannot be out-voted by a permissive gate verdict.
3. **Deliberative layer** — recorded; reimplemented with real logic in Stage 3.

Output: an Ed25519-signed grant, **byte-compatible** with the existing Horus-side verifier
(`app/governance/signed_approver.py`). REQUIRE_HUMAN outcomes become pending requests a
human resolves; BLOCK mints nothing.

## API

- `GET /status` — liveness, `policy_version`, `log_records`, and the **public key** for grant verification.
- `POST /govern` — `{plan, binding{capability,application,plan_sha256,execution_target,session_id,principal_id,action_id}, context_snapshot?, reversible?, governance_vector?, ttl_seconds?}`
  → `GRANTED` (with signed grant) | `PENDING_HUMAN` (pending_id) | `BLOCKED`.
- `POST /pending/{id}/approve` — human resolves a pending request (bearer `LOGOSECO_APPROVER_TOKEN`; Stage-1b will harden this to per-approver signed input).
- `GET /grants/{id}` · `GET /audit` — provenance.

## Provenance of the code (honest labelling)

- `app/governance/*` — reused from `ProjexxAO/padawan@daf097f` (`app/core`). 5 modules are byte-identical
  to `DWBoag/horus-cloud`; **`signed_approver.py` is 2 days behind horus-cloud (8659 vs 9625 bytes) —
  SYNC to the horus-cloud version before production.**
- `app/floor/*` — vendored from `logoseco-engine`'s `governance-floor-standard` (clean, tested, with SPEC
  and EU AI Act / NIST AI RMF mapping under `app/floor/_standard/`).
- `app/approver.py`, `app/decision.py`, `app/store.py`, `app/main.py` — new for this service.

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload       # dev: generates an EPHEMERAL key (lost on restart)
pytest -q                            # 13 tests
```

For production, set `LOGOSECO_PRIVATE_KEY_PEM` (Ed25519 PKCS8), `LOGOSECO_POLICY_VERSION`,
`LOGOSECO_APPROVER_TOKEN`, and the service's own `SUPABASE_*`.

## Not yet done (tracked)
- SupabaseStore (swap for `InMemoryStore`) once the service's Supabase project exists.
- Deploy on Render; publish the public key to Horus.
- Horus-side adapter (Stage 2) — HTTP transport reusing the existing grant verification.
- Deliberative layer real logic (Stage 3).
- Harden the human-approval auth (Stage-1b).
