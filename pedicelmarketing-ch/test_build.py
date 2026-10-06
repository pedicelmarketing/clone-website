"""python3 -m unittest test_build -v"""
import hashlib, tempfile, unittest
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


class AssetVersions(unittest.TestCase):
    """/assets/* is cached immutable for a year, so each reference must change when the file does."""

    def setUp(self):
        self.assets = Path(tempfile.mkdtemp())
        (self.assets / "img").mkdir()
        (self.assets / "a.css").write_text("body{}")
        (self.assets / "img" / "x.webp").write_bytes(b"RIFF")

    def v(self, rel: str) -> str:
        return hashlib.sha256((self.assets / rel).read_bytes()).hexdigest()[:8]

    def test_href_and_src_get_content_hash(self):
        html = ('<link href="/assets/a.css" rel="stylesheet"><img src="/assets/img/x.webp">'
                '<a href="/_external/y.css">e</a><a href="/services/">s</a>')
        out = build.version_assets(html, self.assets)
        self.assertIn(f'href="/assets/a.css?v={self.v("a.css")}"', out)
        self.assertIn(f'src="/assets/img/x.webp?v={self.v("img/x.webp")}"', out)
        self.assertIn('href="/_external/y.css"', out)
        self.assertIn('href="/services/"', out)

    def test_changed_file_changes_url_missing_file_untouched(self):
        html = '<link href="/assets/a.css"><script src="/assets/gone.js"></script>'
        before = build.version_assets(html, self.assets)
        (self.assets / "a.css").write_text("body{color:red}")
        after = build.version_assets(html, self.assets)
        self.assertNotEqual(before, after)
        self.assertIn('src="/assets/gone.js"', after)

    def test_build_output_is_versioned(self):
        root = Path(tempfile.mkdtemp())
        (root / "pages").mkdir()
        (root / "pages" / "index.html").write_text(PAGE.replace("<head>", '<head><link href="/assets/a.css" rel="stylesheet">'))
        build.PAGES, build.STRINGS, build.DIST, build.ASSETS = (
            root / "pages", root / "strings", root / "dist", self.assets)
        build.MIRROR = root / "no-mirror"
        self.assertEqual(build.main(["--lang", "en"]), 0)
        out = (root / "dist" / "en" / "index.html").read_text()
        self.assertIn(f'/assets/a.css?v={self.v("a.css")}', out)
        self.assertTrue((root / "dist" / "assets" / "a.css").is_file())


if __name__ == "__main__":
    unittest.main()
