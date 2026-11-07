# The Governance Floor Standard — Specification

**Version 1.0**

This document is the standard itself. It is written to be checked, not taken on trust. This repository is a reference implementation of it, and its test suite (`tests/`) is a direct, runnable proof of every claim made below.

## The one rule

**No dimension may be compensated for by another.**

An organisation's AI cannot be certified against this standard if even one of five measured dimensions is weak — no matter how strong the other four are, and no matter what the blended score works out to. This is a hard, mathematical bright line, not a stated intention.

This is the specific way this standard differs from most existing AI-governance frameworks and audit approaches: they typically reduce to a weighted or averaged score at some stage — a place where a real weakness in one area can be diluted by strength elsewhere until it disappears into an acceptable-looking blended number. This standard is engineered so that cannot happen.

## The five dimensions

| Dimension | Measures |
|---|---|
| **Honesty** | Does the system do what it claims? Is there a gap between stated behaviour and actual behaviour? |
| **Fairness** | Does it treat the people affected by it equitably? |
| **Consistency** | Are commitments held over time, especially when holding them is costly? |
| **Learning** | Does the organisation change its behaviour in response to what audits find? |
| **Impact** | Does it produce genuine outcomes for real people, not just theatre of compliance? |

Each dimension is scored 0.0–1.0 from independent audit evidence — never asserted, never self-reported by the organisation being certified. **This standard does not specify how you produce these five numbers** — that's the auditing methodology, which can vary by implementer. It specifies what you must do with them once you have them.

## The two gates

Certification requires **both** of the following to hold. Either one failing voids certification outright.

**Gate 1 — Dimension floor.** Every one of the five dimensions must individually score at or above a floor (default **0.5**). A single dimension below the floor voids certification, full stop, regardless of the other four.

**Gate 2 — Blended threshold.** The five dimensions combine via **harmonic mean**, not an arithmetic average, into a single blended score. That blended score must independently reach a threshold (default **0.7**) even after Gate 1 passes.

```
blended_score = 5 / (1/honesty + 1/fairness + 1/consistency + 1/learning + 1/impact)

certified = (all five dimensions >= dimension_floor) AND (blended_score >= blended_threshold)
```

The harmonic mean is what makes Gate 2 meaningful rather than redundant with Gate 1: a set of scores that all just barely clear the floor will itself produce a blended score close to the floor, not the threshold — genuine strength across all five dimensions is required to clear both gates, not just the absence of a single catastrophic one.

### Worked example

Four dimensions strong, one weak:

| Honesty | Fairness | Consistency | Learning | Impact | Blended score |
|---|---|---|---|---|---|
| 0.95 | 0.95 | 0.95 | 0.95 | **0.20** | **0.5429** |

Under a weighted or averaged standard, a blended score of 0.54 might plausibly read as a passable, middling result. Under this standard: **certification is void**, because Impact (0.20) falls below the 0.5 floor. The other four dimensions being excellent does not buy that back. This exact case is `test_the_disqualifying_case_four_strong_one_weak` in `tests/test_certification.py` — run it yourself.

## Verifying a certification independently

Given the five raw dimension scores behind any issued certification, anyone can check it without this library, with a calculator:

1. Confirm all five are individually ≥ the stated floor. If any is not, the certification must be void.
2. Recompute the harmonic mean using the formula above. Confirm it is ≥ the stated threshold.
3. Both must hold for `certified: true`.

This library's `evaluate()` function does exactly this and nothing more — no network calls, no hidden state.

## Immutability and hash-chained history

A conforming implementation should treat each certification as a discrete, dated event — never edited or deleted. A later re-audit produces a **new** certification record, and the full history (including voided certifications) remains queryable.

Each record should be cryptographically chained to the previous one for the same subject (SHA-256 over the record's own content plus the previous record's hash). Altering any past record breaks every hash computed after it. This library's `verify_chain()` function independently checks this, given a list of records an implementer's system returns — it does not trust the implementer's own claim that the chain is intact, it recomputes and confirms.

**Honest limitation:** hash-chaining makes tampering *detectable*, given the tamper-evident chain. It does not make tampering with an implementer's own database *physically impossible* — that depends on the implementer's own operational practices (e.g. never exposing an update/delete code path against certification records). This library gives you the means to check whether a chain has in fact been tampered with; it cannot guarantee an implementer never will.

## What this standard does not claim

- This is a scoring and certification standard for AI governance behaviour, not legal advice, and not a substitute for jurisdiction-specific regulatory compliance.
- It does not specify or guarantee the quality of the underlying audit evidence — only that whatever evidence you have, this standard's aggregation cannot launder a real weakness into an acceptable-looking blended number.

## Versioning

This is Version 1.0. A conforming certification record should record which version of this standard it was evaluated against. If the default floor, threshold, or the formula itself changes in a future version, existing certifications should keep the version they were actually issued against.
