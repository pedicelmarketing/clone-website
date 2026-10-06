"""python3 -m unittest test_build -v"""
import tempfile, unittest
from pathlib import Path
import build

PAGE = "<html><head><title>Home</title></head><body><p>Hello</p></body></html>"


class Lang(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        (root / "pages").mkdir()
        (root / "pages" / "index.html").write_text(PAGE)
        (root / "strings").mkdir()
        for lang in ("de", "fr"):
            (root / "strings" / f"{lang}.json").write_text('{"Home": "H", "Hello": "Hi"}')
        build.PAGES, build.STRINGS, build.DIST, build.ASSETS = (
            root / "pages", root / "strings", root / "dist", root / "assets")
        build.MIRROR = root / "no-mirror"
        self.dist = root / "dist"

    def test_lang_filter_builds_only_that_language(self):
        self.assertEqual(build.main(["--lang", "fr"]), 0)
        self.assertTrue((self.dist / "fr" / "index.html").exists())
        self.assertFalse((self.dist / "index.html").exists())
        self.assertFalse((self.dist / "en").exists())
        sitemap = (self.dist / "sitemap.xml").read_text()
        for url in ("https://pedicelmarketing.ch/", "https://pedicelmarketing.ch/fr/", "https://pedicelmarketing.ch/en/"):
            self.assertIn(url, sitemap)

    def test_default_builds_all_and_bad_args_error(self):
        self.assertEqual(build.main([]), 0)
        for p in ("index.html", "fr/index.html", "en/index.html"):
            self.assertTrue((self.dist / p).exists(), p)
        with self.assertRaises(SystemExit):
            build.main(["--lang", "xx"])
        with self.assertRaises(SystemExit):
            build.main(["--bogus"])


if __name__ == "__main__":
    unittest.main()
