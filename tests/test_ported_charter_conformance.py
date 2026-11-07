import unittest

from app.governance.charter_conformance import CHARTER_REQUIREMENTS, assess_charter_conformance


class CharterConformanceTests(unittest.TestCase):
    def test_empty_evidence_never_claims_conformance(self):
        result = assess_charter_conformance()
        self.assertEqual(result["status"], "NOT_PROVEN")
        self.assertEqual(result["counts"]["not_proven"], len(CHARTER_REQUIREMENTS))
        self.assertFalse(result["independent_conformance_verified"])
        self.assertFalse(result["authority_granted"])

    def test_complete_evidence_is_only_ready_for_independent_review(self):
        evidence = {
            item["id"]: {"status": "VERIFIED", "evidence_ref": "test://" + item["id"],
                         "reviewer": "independent reviewer", "reviewed_at": "2026-10-09T00:00:00Z"}
            for item in CHARTER_REQUIREMENTS
        }
        result = assess_charter_conformance({"evidence": evidence})
        self.assertEqual(result["status"], "READY_FOR_INDEPENDENT_REVIEW")
        self.assertFalse(result["independent_conformance_verified"])
        self.assertFalse(result["execution_performed"])

    def test_failed_evidence_blocks_assessment(self):
        requirement_id = CHARTER_REQUIREMENTS[0]["id"]
        result = assess_charter_conformance({"evidence": {requirement_id: {"status": "FAILED"}}})
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["failed_requirement_ids"], [requirement_id])

    def test_verified_without_review_metadata_is_rejected(self):
        requirement_id = CHARTER_REQUIREMENTS[0]["id"]
        result = assess_charter_conformance({"evidence": {requirement_id: {"status": "VERIFIED"}}})
        self.assertEqual(result["status"], "ASSESSMENT_REJECTED")

    def test_unknown_requirement_is_rejected(self):
        result = assess_charter_conformance({"evidence": {"MADE_UP": {"status": "VERIFIED"}}})
        self.assertEqual(result["status"], "ASSESSMENT_REJECTED")

    def test_non_object_and_non_object_evidence_are_rejected(self):
        self.assertEqual(assess_charter_conformance([])["status"], "ASSESSMENT_REJECTED")
        self.assertEqual(assess_charter_conformance({"evidence": []})["status"], "ASSESSMENT_REJECTED")


if __name__ == "__main__":
    unittest.main()
