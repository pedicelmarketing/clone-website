"""python3 -m unittest deploy/test_form_spam.py — the bot posts seen in Oct 2026 are dropped, real people are not."""
import unittest
from form_handler import FORMS, spam_signs

CONTACT = FORMS["/api/forms/contact"]
AUDIT = FORMS["/api/forms/audit"]


class SpamSigns(unittest.TestCase):
    def test_bot_posts_are_spam(self):
        bots = [
            (CONTACT, {"name-2": "QXWVImEQNDckswyiJqR", "Email-2": "u.x.i.xe.w.a.778@gmail.com", "Phone-Number-2": "9996002672", "Message-2": "joiVDIyYnbUPlGenS"}),
            (CONTACT, {"name-2": "MdSGXradLGdlqwLFCULIRu", "Email-2": "m.ar.yja.c.k.s.on.suby.5r.c.un@gmail.com", "Message-2": "XMUhcyJWDmecMUUiw"}),
            (AUDIT, {"Name": "CajnTWukTnPKIJBJXGKihoQ", "Email": "m.ar.yja.c.k.s.on.suby.5r.c.un@gmail.com", "Position": "aIAgYklXgLzYXIsjGqaJ", "Marketing-Goals": "6436437081"}),
        ]
        for spec, fields in bots:
            self.assertGreaterEqual(len(spam_signs(fields, spec)), 2, fields)

    def test_people_are_not(self):
        people = [
            (CONTACT, {"name-2": "Adrian Garcia Ramos", "Email-2": "partnership@pathmonk.com", "Message-2": "Hi, This is Adrian from Pathmonk"}),
            (CONTACT, {"name-2": "Chukwuemeka Okonkwo", "Email-2": "c.okonkwo@leadway.com", "Message-2": "We need help with LinkedIn"}),
            (AUDIT, {"Name": "Arnold Schwarzenegger", "Email": "arnold@example.com", "Position": "CEO", "Marketing-Goals": "More bookings"}),
        ]
        for spec, fields in people:
            self.assertLess(len(spam_signs(fields, spec)), 2, fields)


if __name__ == "__main__":
    unittest.main()
