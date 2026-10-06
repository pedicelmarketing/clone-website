"""python3 -m unittest pedicelmarketing-ch/test_checks.py"""
import tempfile, unittest
from pathlib import Path
from checks import problems

OK = ('<html lang="de"><head><link rel="canonical" href="https://pedicelmarketing.ch/">'
      '<link rel="alternate" hreflang="de" href="https://pedicelmarketing.ch/"></head>'
      '<body><a href="/services">x</a></body></html>')


def site(pages: dict[str, str]) -> Path:
    root = Path(tempfile.mkdtemp())
    for route, html in pages.items():
        f = root / route.strip("/") / "index.html"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(html)
    return root


class Checks(unittest.TestCase):
    def test_clean_site_passes(self):
        self.assertEqual(problems(site({"/": OK, "/services": OK})), [])

    def test_each_rule_fires(self):
        bad = {   # name -> (html, keyword the problem line must contain)
            "eszett": (OK.replace("x<", "Strasse Straße<"), "forbidden"),
            "price": (OK.replace("x<", "ab CHF 2'900<"), "price"),
            "fake number": (OK.replace("x<", "10.8% engagement<"), "forbidden"),
            "leftover name": (OK.replace("x<", "Vanguard Medical Solutions<"), "forbidden"),
            "blog link": (OK.replace('href="/services"', 'href="/blog"'), "blog link"),
            "broken link": (OK.replace('href="/services"', 'href="/nope"'), "broken link"),
            "no canonical": (OK.replace('rel="canonical"', 'rel="x"'), "no canonical"),
            "no hreflang": (OK.replace('hreflang="de"', 'data-x="de"'), "no hreflang"),
        }
        for name, (html, keyword) in bad.items():
            with self.subTest(name):
                found = problems(site({"/": html, "/services": OK}))
                self.assertTrue(found, name)
                self.assertTrue(any(keyword in p for p in found), f"{name}: {found}")

    def test_attribute_values_are_scanned(self):
        for name, html in {
            "eszett in meta": OK.replace("</head>", '<meta name="description" content="Grüsse ß"></head>'),
            "name in meta": OK.replace("</head>", '<meta property="og:title" content="Vanguard Medical"></head>'),
            "name in alt": OK.replace("x<", '<img src="/a.webp" alt="Vanguard Medical"><'),
            "number in alt": OK.replace("x<", '<img src="/a.webp" alt="10.8% more"><'),
            "price in placeholder": OK.replace("x<", '<input placeholder="CHF 900"><'),
        }.items():
            with self.subTest(name):
                self.assertTrue(problems(site({"/": html, "/services": OK})), name)

    def test_price_rule_word_boundaries_and_swiss_forms(self):
        for text, flagged in [("2 Europäer", False), ("Der Eurostar", False), ("Fr 5 Gruppen", False),
                              ("ab CHF 2'900", True), ("Fr. 900", True), ("2'900.–", True),
                              ("900 EUR", True), ("€ 5", True), ("5 €", True)]:
            with self.subTest(text):
                found = [p for p in problems(site({"/": OK.replace("x<", text + "<"), "/services": OK})) if "price" in p]
                self.assertEqual(bool(found), flagged, text)

    def test_unsourced_old_site_stats_are_forbidden(self):
        for text in ["1000+ leads", "60%+ awareness", "80+ projects", "100% of the brands", "over 30 years",
                     "#3 SEO", "100 % Zielerreichung", "über 30 Jahre", "plus de 30 ans", "100 % des marques"]:
            with self.subTest(text):
                found = problems(site({"/": OK.replace("x<", text + "<"), "/services": OK}))
                self.assertTrue(any("forbidden" in p for p in found), f"{text}: {found}")

    def test_script_and_style_text_is_not_visible_text(self):
        html = OK.replace("<body>", "<body><style>.a{width:250%}</style><script>var x='Vanguard Medical'</script>")
        self.assertEqual(problems(site({"/": html, "/services": OK})), [])

    def test_external_mirror_is_not_walked(self):
        root = site({"/": OK, "/services": OK})
        mirror = Path(tempfile.mkdtemp())             # stands in for the 122 MB symlinked mirror
        (mirror / "x").mkdir()
        (mirror / "x" / "index.html").write_text("<html><body>Vanguard Medical Straße</body></html>")
        (root / "_external").symlink_to(mirror)
        self.assertEqual(problems(root), [])
        (root / "_external").unlink()                 # and a real dir is skipped too
        shutil_dir = root / "_external" / "x"
        shutil_dir.mkdir(parents=True)
        (shutil_dir / "index.html").write_text("<html><body>Vanguard Medical</body></html>")
        self.assertEqual(problems(root), [])


if __name__ == "__main__":
    unittest.main()
