"""python3 -m unittest deploy/test_form_pitch.py — a free-audit request queues a pitch for the new lead."""
import json
import unittest
from form_handler import FORMS, pitch_payload

AUDIT = FORMS["/api/forms/audit"]
CONTACT = FORMS["/api/forms/contact"]
CRM_OK = "crm 200 " + json.dumps({"contact_id": "c-123", "deal_id": "d-1", "activity_id": "a-1"})


class PitchPayload(unittest.TestCase):
    def test_audit_with_website_queues_a_pitch(self):
        p = pitch_payload(AUDIT, {"Name": "Ana", "Email": "ana@x.es", "Company-Website": "lacabreramarbella.es"}, CRM_OK)
        self.assertEqual(p, {"p_url": "lacabreramarbella.es", "p_contact_id": "c-123", "p_depth": "light", "p_origin": "inbound"})

    def test_no_website_or_contact_form_queues_nothing(self):
        self.assertIsNone(pitch_payload(AUDIT, {"Name": "Ana", "Email": "ana@x.es"}, CRM_OK))
        self.assertIsNone(pitch_payload(CONTACT, {"name-2": "Ana", "Email-2": "ana@x.es"}, CRM_OK))

    def test_unreadable_crm_answer_queues_nothing(self):
        self.assertIsNone(pitch_payload(AUDIT, {"Company-Website": "x.es"}, "crm 200 not-json"))


if __name__ == "__main__":
    unittest.main()
