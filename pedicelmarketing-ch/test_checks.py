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
        bad = {
            "eszett": OK.replace("x<", "Strasse Straße<"),
            "price": OK.replace("x<", "ab CHF 2'900<"),
            "fake number": OK.replace("x<", "10.8% engagement<"),
            "leftover name": OK.replace("x<", "Vanguard Medical Solutions<"),
            "blog link": OK.replace('href="/services"', 'href="/blog"'),
            "broken link": OK.replace('href="/services"', 'href="/nope"'),
            "no canonical": OK.replace('rel="canonical"', 'rel="x"'),
        }
        for name, html in bad.items():
            with self.subTest(name):
                self.assertTrue(problems(site({"/": html, "/services": OK})), name)

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
