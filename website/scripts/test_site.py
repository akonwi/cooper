"""No-build site checks using only Python's standard library."""
from html.parser import HTMLParser
from pathlib import Path
import unittest
from urllib.parse import urljoin, urlsplit

WEBSITE = Path(__file__).resolve().parents[1]
PUBLIC = WEBSITE / "public"
MICA = "https://cdn.jsdelivr.net/npm/@akonwi/mica@0.14.0/mica.css"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.code = ""
        self.in_code = False
        self.feed((PUBLIC / "index.html").read_text())

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))
        if tag == "code":
            self.in_code = True

    def handle_endtag(self, tag):
        if tag == "code":
            self.in_code = False

    def handle_data(self, data):
        if self.in_code:
            self.code += data


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.page = Page()

    def test_static_page_and_styles(self):
        tags = [tag for tag, _ in self.page.elements]
        self.assertEqual(tags.count("h1"), 1)
        self.assertNotIn("script", tags)
        self.assertIn(("html", {"lang": "en"}), self.page.elements)
        self.assertIn(("main", {"id": "main"}), self.page.elements)
        styles = [a["href"] for t, a in self.page.elements
                  if t == "link" and a.get("rel") == "stylesheet"]
        self.assertEqual(styles, [MICA, "style.css"])
        self.assertEqual(list(PUBLIC.glob("*.html")), [PUBLIC / "index.html"])

    def test_local_targets_at_root_and_repository_path(self):
        ids = {a["id"] for _, a in self.page.elements if "id" in a}
        for base in ("/", "/cooper/"):
            for tag, attrs in self.page.elements:
                if tag == "img":
                    self.assertTrue(attrs.get("alt"))
                for key in ("href", "src", "srcset"):
                    if key not in attrs:
                        continue
                    value = attrs[key]
                    with self.subTest(base=base, target=value):
                        url = urlsplit(urljoin("https://example.test" + base, value))
                        if url.netloc != "example.test":
                            self.assertEqual(url.scheme, "https")
                            continue
                        self.assertTrue(url.path.startswith(base))
                        path = PUBLIC / (url.path[len(base):] or "index.html")
                        self.assertTrue(path.is_file(), str(path))
                        if url.fragment:
                            self.assertIn(url.fragment, ids)

    def test_example_and_recording_match_sources(self):
        self.assertEqual(self.page.code.strip(),
                         (WEBSITE / "snippets/hello.ard").read_text().strip())
        self.assertEqual((PUBLIC / "dashboard.gif").read_bytes(),
                         (WEBSITE.parent / "screenshots/dashboard.gif").read_bytes())
        self.assertIn(("source", {"media": "(prefers-reduced-motion: reduce)",
                                  "srcset": "dashboard.png"}), self.page.elements)


if __name__ == "__main__":
    unittest.main()
