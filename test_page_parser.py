"""
Run:  python -B -m unittest -v test_page_parser
"""


import unittest
from types import SimpleNamespace
 
import page_parser
from page_parser import (parse_page, OK, REDIRECT, HTTP_ERROR, CACHE_ERROR,
                         NO_RESPONSE, OUT_OF_SCOPE, NOT_HTML, TOO_LARGE, EMPTY)
from analytics import visible_words 
from url_utils import get_links
from trap_detector import is_low_information  


URL = "https://www.ics.uci.edu/about"
HTML = (b"<html><head><title>Title words</title><style>.x{}</style></head>"
        b"<body><script>var hidden = 1;</script><h1>About ICS</h1>"
        b"<p>The Donald Bren School of Information and Computer Sciences.</p>"
        b"<a href='/people'>People</a> <a href='research#top'>Research</a>"
        b"<a href='https://www.google.com/'>Out</a></body></html>")
 

def make_resp(status=200, content=HTML, url=URL, final_url=None,
              headers=None, error=None, raw=True):
    """Fake object shaped like utils.response.Response """
    if headers is None:
        headers = {"Content-Type": "text/html; charset=utf-8"}
    raw_response = SimpleNamespace(url=final_url or url, content=content,
                                   headers=headers) if raw else None
    return SimpleNamespace(url=url, status=status, error=error, raw_response=raw_response)



class TestPageParser(unittest.TestCase):
    # ------------------------------------------------ 1. normal HTML pages
    def test_ok_page(self):
        """A normal page is OK and its text has no markup, scripts, styles or <head>."""
        page = parse_page(URL, make_resp())
        self.assertTrue(page.ok)
        self.assertEqual((page.status, page.http_status, page.final_url), (OK, 200, URL))
        self.assertIn("Donald Bren School", page.text)
        for hidden in ("hidden", ".x", "Title words", "<p>"):
            self.assertNotIn(hidden, page.text)

    def test_content_type_variants(self):
        """HTML is recognised with missing/odd headers; type is normalised."""
        for headers in ({}, None, {"Content-Type": "application/xhtml+xml"},
                        {"Content-Type": "TEXT/HTML; Charset=UTF-8"}):
            with self.subTest(headers=headers):
                self.assertEqual(parse_page(URL, make_resp(headers=headers)).status, OK)
        page = parse_page(URL, make_resp(headers={"Content-Type": "TEXT/HTML; Charset=UTF-8"}))
        self.assertEqual(page.content_type, "text/html")    

    def test_encodings(self):
        """UTF-8 without charset header, <meta charset>, and bad bytes all decode."""
        utf8 = "<p>café 中文</p>".encode("utf-8")
        self.assertIn("café", parse_page(URL, make_resp(
            content=utf8, headers={"Content-Type": "text/html"})).text)
        latin1 = ("<head><meta charset='iso-8859-1'></head><p>café</p>").encode("latin-1")
        self.assertIn("café", parse_page(URL, make_resp(
            content=latin1, headers={"Content-Type": "text/html"})).text)
        broken = parse_page(URL, make_resp(content=b"<p>ok \xff\xfe words</p>"))
        self.assertEqual(broken.status, OK)
        self.assertIn("ok", broken.words)

    def test_redirect_out_of_scope(self):
        """Redirects leaving the 4 domains (incl. look-alikes) are not indexed."""
        for bad in ("https://www.uci.edu/", "https://ics.uci.edu.evil.com/",
                    "https://notics.uci.edu/", "https://physics.uci.edu/"):
            with self.subTest(final_url=bad):
                page = parse_page(URL, make_resp(final_url=bad))
                self.assertEqual(page.status, OUT_OF_SCOPE)
                self.assertEqual(page.text, "")

    def test_http_errors(self):
        """Non-200 codes are errors and carry nothing to index."""
        for code in (403, 404, 500, 204, None):
            with self.subTest(status=code):
                page = parse_page(URL, make_resp(status=code))
                self.assertEqual(page.status, HTTP_ERROR)
                self.assertEqual((page.html, page.text, page.words), ("", "", []))

    def test_dead_pages(self):
        """200 with no body, only whitespace, or no visible text is EMPTY"""
        for body in (b"", b"   \n ", b"<head><title>t</title></head><script>x()</script>"):
            with self.subTest(body=body):
                self.assertEqual(parse_page(URL, make_resp(content=body)).status, EMPTY)

