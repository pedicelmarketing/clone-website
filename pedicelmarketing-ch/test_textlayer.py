"""python3 -m unittest pedicelmarketing-ch/test_textlayer.py"""
import re, unittest
from bs4 import BeautifulSoup
from textlayer import strings_in, localize, MissingTranslation, prefix

PAGE = """<!DOCTYPE html><html data-wf-domain="www.pedicelmarketing.com"><head><title>Home</title>
<meta name="description" content="We grow you"><meta property="og:title" content="Home">
<meta property="og:image" content="/_external/preview.jpg"><meta name="twitter:image" content="/_external/preview.jpg">
<link rel="stylesheet" href="/_external/x.css"></head><body>
<nav><a href="/">Home</a><a href="/services">Services</a><a href="/projects/coeo#results">Coeo</a><div data-lang-switch></div></nav>
<p>Hello <b>world</b></p><p>&nbsp;</p><p>‍</p><p>   </p>
<img src="/_external/a.webp" alt="Team at work">
<form><input type="submit" value="Send" data-wait="Please wait..."><input placeholder="Your email"></form>
<a href="/_external/f.pdf">PDF</a><a href="mailto:info@x.ch">Mail</a><a href="#top">Top</a>
<a href="https://linkedin.com/x">LinkedIn</a><a href="/api/forms/ch-contact">api</a>
<script>var s = "not text";</script></body></html>"""

DE = {"Home": "Startseite", "We grow you": "Wir lassen Sie wachsen", "Services": "Leistungen",
      "Hello": "Hallo", "world": "Welt", "Team at work": "Team bei der Arbeit", "Send": "Senden",
      "Please wait...": "Bitte warten...", "Your email": "Ihre E-Mail", "PDF": "PDF", "Mail": "E-Mail",
      "Top": "Nach oben", "LinkedIn": "LinkedIn", "api": "api", "Coeo": "Coeo"}


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


    def test_zero_width_chars_stripped_from_keys(self):
        html = "<html><head><title>T</title></head><body><p>Hello\u200d</p><p>\ufeffWor\u200bld\u200c</p></body></html>"
        self.assertEqual(strings_in(html), ["T", "Hello", "World"])
        out = localize(html, "de", "/", {"T": "T", "Hello": "Hallo", "World": "Welt"})
        self.assertIn("Hallo", out)
        self.assertIn("Welt", out)


class Localize(unittest.TestCase):
    def test_translates_and_sets_lang(self):
        out = localize(PAGE, "de", "/", DE)
        self.assertRegex(out, r'<html[^>]*\blang="de-CH"')
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
        self.assertIn('href="/fr/services/"', out)
        self.assertIn('href="/fr/projects/coeo/#results"', out)
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
        self.assertEqual(alt, {"de-CH": "https://pedicelmarketing.ch/services/",
                               "fr-CH": "https://pedicelmarketing.ch/fr/services/",
                               "en": "https://pedicelmarketing.ch/en/services/",
                               "x-default": "https://pedicelmarketing.ch/services/"})
        self.assertIn('class="lang-switch"', out)
        self.assertIn('aria-current="true"', out)          # FR marked current
        self.assertIn('data-wf-domain="pedicelmarketing.ch"', out)
        self.assertEqual(soup.html["lang"], "fr-CH")
        self.assertEqual([a["hreflang"] for a in soup.select(".lang-switch a")], ["de-CH", "fr-CH", "en"])


class Links(unittest.TestCase):
    def test_page_links_get_a_trailing_slash_files_and_suffixes_handled(self):
        for href, de, fr in [
            ("/services", "/services/", "/fr/services/"),
            ("/services/", "/services/", "/fr/services/"),
            ("/", "/", "/fr/"),
            ("/projects/coeo#results", "/projects/coeo/#results", "/fr/projects/coeo/#results"),
            ("/audit?ref=nav", "/audit/?ref=nav", "/fr/audit/?ref=nav"),
            ("/#top", "/#top", "/fr/#top"),
            ("/sitemap.xml", "/sitemap.xml", "/sitemap.xml"),
            ("/assets/a.css", "/assets/a.css", "/assets/a.css"),
        ]:
            page = f'<html><head><title>T</title></head><body><a href="{href}">T</a></body></html>'
            for lang, want in (("de", de), ("fr", fr)):
                with self.subTest(href=href, lang=lang):
                    got = BeautifulSoup(localize(page, lang, "/", {"T": "T"}), "lxml").body.a["href"]
                    self.assertEqual(got, want)


class Social(unittest.TestCase):
    def test_absolute_images_og_url_and_locale(self):
        for lang, route, url, locale in [("de", "/", "https://pedicelmarketing.ch/", "de_CH"),
                                         ("fr", "/services/", "https://pedicelmarketing.ch/fr/services/", "fr_CH"),
                                         ("en", "/services/", "https://pedicelmarketing.ch/en/services/", "en")]:
            with self.subTest(lang):
                soup = BeautifulSoup(localize(PAGE, lang, route, {k: k for k in DE}), "lxml")
                meta = lambda **kw: [m["content"] for m in soup.find_all("meta", attrs=kw)]
                self.assertEqual(meta(property="og:image"), ["https://pedicelmarketing.ch/_external/preview.jpg"])
                self.assertEqual(meta(name="twitter:image"), ["https://pedicelmarketing.ch/_external/preview.jpg"])
                self.assertEqual(meta(property="og:url"), [url])
                self.assertEqual(meta(property="og:url"), [soup.find("link", rel="canonical")["href"]])
                self.assertEqual(meta(property="og:locale"), [locale])
                self.assertEqual(meta(name="robots"), [])

    def test_404_route_is_noindex(self):
        soup = BeautifulSoup(localize(PAGE, "fr", "/404/", {k: k for k in DE}), "lxml")
        self.assertEqual([m["content"] for m in soup.find_all("meta", attrs={"name": "robots"})], ["noindex"])


if __name__ == "__main__":
    unittest.main()
