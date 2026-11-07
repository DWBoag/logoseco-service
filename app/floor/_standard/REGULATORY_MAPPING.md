# Regulatory Mapping — Governance Floor Standard v1.0

**Version 1.0** — companion to `SPEC.md`, not a replacement for it.

This document maps the Governance Floor Standard's five dimensions and two-gate rule to provisions of the **EU AI Act** and functions of the **NIST AI Risk Management Framework (AI RMF 1.0)**. It exists to answer a concrete question a compliance team actually has: *if we adopt this standard, which of our existing obligations does it help us satisfy?*

## What this document is not

This is not legal advice, and adopting the Governance Floor Standard does not by itself constitute compliance with the EU AI Act, NIST AI RMF, or any other regulatory regime. The mapping below is a correspondence of *concepts*, not a certification of *conformance* — an organisation's actual legal obligations depend on its specific system, its risk classification, and its jurisdiction, none of which this document can determine. Consult qualified counsel for an actual compliance determination. This document was written from the publicly available text of the EU AI Act (Regulation (EU) 2024/1689) and NIST AI 100-1, current as of 2026-07-12; verify against the current text before relying on it, as both frameworks continue to be interpreted and, in the EU AI Act's case, phased in.

## Why a floor rule maps onto compliance obligations at all

Both frameworks converge on the same structural point the Governance Floor Standard is built around: **a single serious deficiency is not supposed to be offset by strength elsewhere.** The EU AI Act's Article 9 risk management system requires risks to be identified and addressed individually, not netted against unrelated system strengths. NIST's AI RMF lists seven independent trustworthiness characteristics precisely because a system strong on five and badly deficient on a sixth is not, in NIST's own framing, trustworthy — the characteristics are conjunctive, not a weighted composite. Neither framework specifies the *arithmetic* for combining sub-scores the way this standard does; the correspondence below is conceptual, not a claim that either framework mandates a harmonic mean specifically.

## Dimension-by-dimension mapping

| Dimension | EU AI Act (Regulation (EU) 2024/1689) | NIST AI RMF 1.0 |
|---|---|---|
| **Honesty** | Article 13 — Transparency and provision of information to deployers: system operation must be "sufficiently transparent to enable deployers to interpret [its] output," with accurate disclosure of capabilities, limitations, and accuracy. | *Valid and reliable* + *Accountable and transparent* — the system performs as claimed for its intended purpose, and information about it is honestly disclosed. |
| **Fairness** | Article 10 — Data governance: training/validation/testing data must be "relevant, sufficiently representative, and... free of errors" with respect to the persons or groups the system affects. | *Fair — harmful bias managed* — outputs are just and equitable, without unjustified disparate impact on individuals or groups. |
| **Consistency** | Article 15 — Accuracy, robustness and cybersecurity: the system must "perform consistently" and be resilient against degradation over its lifecycle, not just at initial testing. | *Valid and reliable* (the reliability half specifically) — consistent behaviour under expected conditions over time, not a one-time benchmark result. |
| **Learning** | Article 9(2) — the risk management system is explicitly "a continuous iterative process... requiring regular systematic review and updating" across the system's lifecycle, not a one-off assessment. Article 17's quality management system similarly requires ongoing post-market monitoring. | *Manage* function — allocating resources to identified risks on an ongoing basis, and *Map* being revisited as context changes; the AI RMF's four functions are explicitly iterative, not a single linear pass. |
| **Real Impact** | Article 14 — Human oversight: measures must be "effective," not merely documented — oversight that exists on paper but produces no real change in system behaviour does not satisfy the Article. Article 9(2)(c)-(d) requires evaluating risks from *actual* use, including reasonably foreseeable misuse. | *Safe* — the system must actually protect against physical, psychological, or other harm in practice, which NIST frames as an outcome, not a documentation exercise. |

## The floor rule, mapped

The Governance Floor Standard's core mechanic — every dimension must clear a floor independently, and a single failure voids the outcome regardless of the others — corresponds most directly to:

- **EU AI Act Article 9(1)-(2)**: the risk management system must address risks that are "identified and evaluated" individually; the Act does not contemplate a high-risk system being acceptable because *most* of its risk categories are well-managed while one is not. A provider cannot argue that excellent data governance offsets inadequate human oversight — each Section 2 requirement (Articles 9–15) is independently mandatory for a high-risk system, not tradeable against the others.
- **NIST AI RMF's seven trustworthiness characteristics**: presented as characteristics a trustworthy system has *together*, explicitly including the observation that "trade-offs" between them (e.g. privacy vs. accuracy) require deliberate handling, not silent averaging. A system that scores well on validity but poorly on fairness is not, under NIST's own framing, trustworthy merely because the average looks acceptable.

Neither framework specifies numeric floors or a harmonic-mean formula — that specific mechanism (0.5 dimension floor, 0.7 blended threshold via harmonic mean) is the Governance Floor Standard's own contribution, offered as one concrete, checkable way to operationalize a principle both frameworks already state conceptually but leave to the implementer to formalize.

## Honest limitations

- **This is a concept map, not a crosswalk certified by the EU or NIST.** Neither body has reviewed or endorsed the Governance Floor Standard. No claim here should be read as "the EU AI Act requires a 0.5 floor" — it does not; it requires that risks be individually addressed, which this standard's floor rule is one way (not the only way) to formalize.
- **Regulatory text changes.** The EU AI Act's high-risk provisions (Articles 9–49) are described in current guidance as reaching full applicability around August 2026; verify current applicability dates before relying on this document for a compliance decision.
- **The five dimensions here (honesty, fairness, consistency, learning, impact) are the Governance Floor Standard's own taxonomy**, not a renaming of either framework's categories. The mapping above is a correspondence of intent, not a claim that e.g. "Fairness" and "Article 10" cover identical scope — Article 10 is specifically about training data governance, which is one input to fairness, not the whole of it.

## Provenance

See `SPEC.md` in this repository for the full standard this document maps. This mapping was produced 2026-07-12, grounded in the publicly available text of Regulation (EU) 2024/1689 and NIST AI 100-1, and should be re-verified against current source text before being relied upon for any compliance purpose.
