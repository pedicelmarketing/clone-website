"""python3 -m unittest deploy/test_form_pitch.py — a free-audit request queues a pitch for the new lead."""
import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

import form_handler
from form_handler import FORMS, form_label, notification_html, pitch_payload

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


class SwissForms(unittest.TestCase):
    def test_ch_specs_mirror_com_with_ch_label(self):
        for com, ch in [("/api/forms/audit", "/api/forms/ch-audit"), ("/api/forms/contact", "/api/forms/ch-contact")]:
            self.assertEqual(FORMS[ch]["crm"], FORMS[com]["crm"])
            self.assertEqual(FORMS[ch]["fields"], FORMS[com]["fields"])
            self.assertTrue(FORMS[ch]["label"].endswith("(CH)"))
        self.assertTrue(FORMS["/api/forms/ch-audit"]["pitch"])
        self.assertNotIn("(CH)", FORMS["/api/forms/audit"]["label"])


CH_AUDIT = FORMS["/api/forms/ch-audit"]
CH_CONTACT = FORMS["/api/forms/ch-contact"]


class SwissLanguage(unittest.TestCase):
    def test_label_per_language(self):
        for lang, audit, contact in [("de", "Website Audit request (CH-DE)", "Contact form (CH-DE)"),
                                     ("fr", "Website Audit request (CH-FR)", "Contact form (CH-FR)"),
                                     ("en", "Website Audit request (CH-EN)", "Contact form (CH-EN)"),
                                     ("FR", "Website Audit request (CH-FR)", "Contact form (CH-FR)"),
                                     ("de-CH", "Website Audit request (CH-DE)", "Contact form (CH-DE)")]:
            with self.subTest(lang):
                self.assertEqual(form_label(CH_AUDIT, {"lang": lang}), audit)
                self.assertEqual(form_label(CH_CONTACT, {"lang": lang}), contact)

    def test_missing_or_unknown_language_is_plain_ch(self):
        for fields in ({}, {"lang": ""}, {"lang": "it"}, {"lang": "es"}, {"lang": "<script>"}, {"lang": "x" * 500}):
            with self.subTest(fields):
                self.assertEqual(form_label(CH_CONTACT, fields), "Contact form (CH)")
                self.assertEqual(form_label(CH_AUDIT, fields), "Website Audit request (CH)")

    def test_com_ignores_lang(self):
        for lang in ("de", "fr", "en", ""):
            self.assertEqual(form_label(CONTACT, {"lang": lang}), "Contact form")
            self.assertEqual(form_label(AUDIT, {"lang": lang}), "Website Audit request")
        p = pitch_payload(AUDIT, {"Company-Website": "x.es", "lang": "fr"}, CRM_OK)
        self.assertEqual(p, {"p_url": "x.es", "p_contact_id": "c-123", "p_depth": "light", "p_origin": "inbound"})

    def test_ch_pitch_carries_the_language_when_known(self):
        p = pitch_payload(CH_AUDIT, {"Company-Website": "x.ch", "lang": "fr"}, CRM_OK)
        self.assertEqual(p["p_lang"], "fr")      # pitch_request(p_lang) accepts en/es/de/fr
        self.assertNotIn("p_lang", pitch_payload(CH_AUDIT, {"Company-Website": "x.ch", "lang": "it"}, CRM_OK))

    def test_notification_names_the_site(self):
        entry = {"at": "2026-10-06T12:00:00+00:00", "ip": "1.2.3.4"}
        self.assertIn("on pedicelmarketing.ch.", notification_html(CH_CONTACT, "Contact form (CH-DE)", "", entry))
        self.assertEqual(notification_html(CONTACT, "Contact form", "<tr></tr>", entry),   # .com text unchanged
                         "<p>New submission from the <strong>Contact form</strong> on pedicelmarketing.com.</p>"
                         "<table><tr></tr></table><p style='color:#888;font-size:12px'>Received "
                         "2026-10-06T12:00:00+00:00 from 1.2.3.4</p>")


class HandlerEndToEnd(unittest.TestCase):
    """POST through the real handler; CRM, email and ledger are stubbed and their inputs captured."""

    def post(self, path: str, body: str) -> dict:
        seen = {}
        crm = lambda spec, fields, ext, label=None: (seen.update(crm=label or spec["label"]) or (True, CRM_OK))
        mail = lambda subject, body, reply: (seen.update(subject=subject, body=body) or (True, "ok"))
        pitch = lambda payload: (seen.update(pitch=payload) or (True, "ok"))
        with mock.patch.object(form_handler, "push_to_crm", crm), mock.patch.object(form_handler, "send_via_brevo", mail), \
                mock.patch.object(form_handler, "request_pitch", pitch), mock.patch.object(form_handler, "record", lambda e: seen.update(ledger=e)):
            srv = ThreadingHTTPServer(("127.0.0.1", 0), form_handler.Handler)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{srv.server_port}{path}", data=body.encode(),
                                             headers={"Content-Type": "application/x-www-form-urlencoded"})
                with urllib.request.urlopen(req, timeout=5) as r:
                    self.assertEqual(json.loads(r.read()), {"ok": True})
            finally:
                srv.shutdown()
                srv.server_close()
        return seen

    def test_ch_french_contact(self):
        seen = self.post("/api/forms/ch-contact", "name-2=Anne+Dubois&Email-2=anne%40x.ch&Message-2=Bonjour+merci&website_url_hp=&lang=fr")
        self.assertEqual(seen["crm"], "Contact form (CH-FR)")
        self.assertEqual(seen["subject"], "[Website] Contact form (CH-FR) - anne@x.ch")
        self.assertIn("on pedicelmarketing.ch.", seen["body"])
        self.assertEqual(seen["ledger"]["form"], "Contact form (CH-FR)")

    def test_ch_audit_without_lang_and_pitch_lang(self):
        seen = self.post("/api/forms/ch-audit", "Name=Hans+Meier&Email=hans%40x.ch&Company-Website=x.ch&Position=CEO")
        self.assertEqual(seen["crm"], "Website Audit request (CH)")
        self.assertNotIn("p_lang", seen["pitch"])
        seen = self.post("/api/forms/ch-audit", "Name=Hans+Meier&Email=hans%40x.ch&Company-Website=x.ch&Position=CEO&lang=de")
        self.assertEqual(seen["crm"], "Website Audit request (CH-DE)")
        self.assertEqual(seen["pitch"]["p_lang"], "de")

    def test_com_contact_unchanged_even_with_lang(self):
        seen = self.post("/api/forms/contact", "name-2=Ana+Ruiz&Email-2=ana%40x.es&Message-2=Hola+gracias&lang=fr")
        self.assertEqual(seen["crm"], "Contact form")
        self.assertEqual(seen["subject"], "[Website] Contact form - ana@x.es")
        self.assertIn("<strong>Contact form</strong> on pedicelmarketing.com.</p>", seen["body"])
        self.assertEqual(seen["ledger"]["form"], "Contact form")

    def test_honeypot_short_circuits_ch_forms(self):
        seen = self.post("/api/forms/ch-contact", "name-2=Bot&Email-2=b%40x.ch&website_url_hp=http%3A%2F%2Fspam&lang=de")
        self.assertEqual(seen, {})


if __name__ == "__main__":
    unittest.main()
