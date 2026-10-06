"""python3 -m unittest pedicelmarketing-ch/test_textlayer.py"""
import re, unittest
from bs4 import BeautifulSoup
from textlayer import strings_in, localize, MissingTranslation, prefix

PAGE = """<!DOCTYPE html><html data-wf-domain="www.pedicelmarketing.com"><head><title>Home</title>
<meta name="description" content="We grow you"><meta property="og:title" content="Home">
<link rel="stylesheet" href="/_external/x.css"></head><body>
<nav><a href="/">Home</a><a href="/services">Services</a><div data-lang-switch></div></nav>
<p>Hello <b>world</b></p><p>&nbsp;</p><p>‍</p><p>   </p>
<img src="/_external/a.webp" alt="Team at work">
<form><input type="submit" value="Send" data-wait="Please wait..."><input placeholder="Your email"></form>
<a href="/_external/f.pdf">PDF</a><a href="mailto:info@x.ch">Mail</a><a href="#top">Top</a>
<a href="https://linkedin.com/x">LinkedIn</a><a href="/api/forms/ch-contact">api</a>
<script>var s = "not text";</script></body></html>"""

DE = {"Home": "Startseite", "We grow you": "Wir lassen Sie wachsen", "Services": "Leistungen",
      "Hello": "Hallo", "world": "Welt", "Team at work": "Team bei der Arbeit", "Send": "Senden",
      "Please wait...": "Bitte warten...", "Your email": "Ihre E-Mail", "PDF": "PDF", "Mail": "E-Mail",
      "Top": "Nach oben", "LinkedIn": "LinkedIn", "api": "api"}


class Strings(unittest.TestCase):
    def test_collects_text_attrs_and_meta(self):
        s = strings_in(PAGE)
        for want in ["Home", "We grow you", "Hello", "world", "Team at work", "Send", "Please wait...", "Your email"]:
            self.assertIn(want, s)
        self.assertNotIn("not text", s)
        self.assertEqual(len(s), len(set(s)))

    def test_whitespace_and_zwj_ignored(self):
        s = strings_in(PAGE)
        self.assertFalse(any(not x.strip("‍  \n\t") for x in s))


class Localize(unittest.TestCase):
    def test_translates_and_sets_lang(self):
        out = localize(PAGE, "de", "/", DE)
        self.assertRegex(out, r'<html[^>]*\blang="de"')
        self.assertIn("Hallo", out)
        self.assertIn('content="Wir lassen Sie wachsen"', out)
        self.assertIn('value="Senden"', out)
        self.assertNotIn("Hello", out)

    def test_missing_translation_fails(self):
        with self.assertRaises(MissingTranslation) as ctx:
            localize(PAGE, "fr", "/", {"Home": "Accueil"})
        self.assertIn("Hello", ctx.exception.missing)

    def test_english_needs_no_map(self):
        self.assertIn("Hello", localize(PAGE, "en", "/", {}))

    def test_links_prefixed_only_when_internal(self):
        out = localize(PAGE, "fr", "/", {k: k for k in DE})
        self.assertIn('href="/fr/"', out)
        self.assertIn('href="/fr/services"', out)
        for kept in ['href="/_external/f.pdf"', 'href="mailto:info@x.ch"', 'href="#top"',
                     'href="https://linkedin.com/x"', 'href="/api/forms/ch-contact"', 'href="/_external/x.css"']:
            self.assertIn(kept, out)
        self.assertEqual(prefix("de"), "")

    def test_hreflang_canonical_and_switcher(self):
        out = localize(PAGE, "fr", "/services/", {k: k for k in DE})
        soup = BeautifulSoup(out, "lxml")          # attribute order is not significant
        self.assertEqual([l["href"] for l in soup.find_all("link", rel="canonical")],
                         ["https://pedicelmarketing.ch/fr/services/"])
        alt = {l["hreflang"]: l["href"] for l in soup.find_all("link", rel="alternate")}
        self.assertEqual(alt, {"de": "https://pedicelmarketing.ch/services/",
                               "fr": "https://pedicelmarketing.ch/fr/services/",
                               "en": "https://pedicelmarketing.ch/en/services/",
                               "x-default": "https://pedicelmarketing.ch/services/"})
        self.assertIn('class="lang-switch"', out)
        self.assertIn('aria-current="true"', out)          # FR marked current
        self.assertIn('data-wf-domain="pedicelmarketing.ch"', out)


if __name__ == "__main__":
    unittest.main()
