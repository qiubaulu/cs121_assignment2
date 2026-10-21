"""Offline tests for Assignment 2 counting rules, durability, and integration."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from analytics import Analytics, visible_words


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / "stats.sqlite3"
        self.stats = Analytics(self.path)

    def tearDown(self):
        self.stats.close()
        self.temp.cleanup()

    def test_fragment_deduplication(self):
        self.assertTrue(self.stats.record_page("https://www.ics.uci.edu/a#one", "cat"))
        self.assertFalse(self.stats.record_page("https://www.ics.uci.edu/a#two", "dog"))
        self.assertEqual(self.stats.snapshot()["top_words"], [("cat", 1)])

    def test_distinct_urls_with_same_content(self):
        for url in ["http://ics.uci.edu/a", "https://ics.uci.edu/a",
                    "https://ics.uci.edu/a?x=1", "https://ics.uci.edu/a/"]:
            self.assertTrue(self.stats.record_page(url, "cat"))
        self.assertEqual(self.stats.snapshot()["unique_pages"], 4)
        self.assertEqual(self.stats.snapshot()["top_words"], [("cat", 4)])

    def test_markup_and_noncontent_excluded(self):
        words = visible_words("<head><title>ignore</title></head><style>ignore</style>"
                              "<script>ignore</script><template>ignore</template>"
                              "<!-- ignore --><p>The cat</p><b>runs</b>")
        self.assertEqual(words, ["the", "cat", "runs"])

    def test_longest_includes_stopwords(self):
        self.stats.record_page("https://cs.uci.edu/a", "the and a cat")
        self.stats.record_page("https://stat.uci.edu/b", "dog dog dog")
        result = self.stats.snapshot()
        self.assertEqual(result["longest_page"], ("https://cs.uci.edu/a", 4))
        self.assertEqual(result["top_words"], [("dog", 3), ("cat", 1)])

    def test_top_50_and_ties(self):
        self.stats.record_page("https://cs.uci.edu/", " ".join("term%d" % i for i in range(60)))
        result = self.stats.snapshot()["top_words"]
        self.assertEqual(len(result), 50)
        self.assertEqual(result, [(w, 1) for w in sorted("term%d" % i for i in range(60))[:50]])

    def test_subdomains_sorted_and_scheme_combined(self):
        for host in ["z.ics.uci.edu", "a.ics.uci.edu", "ics.uci.edu", "ics.uci.edu.evil.org"]:
            self.stats.record_page("https://" + host + "/", "cat")
        self.stats.record_page("http://a.ics.uci.edu/", "cat")
        self.assertEqual(self.stats.snapshot()["ics_subdomains"],
                         [("a.ics.uci.edu", 2), ("z.ics.uci.edu", 1)])

    def test_invalid_scope_and_empty_content(self):
        for url in ["https://evil.org/", "ftp://cs.uci.edu/", "http://[broken", None]:
            self.assertFalse(self.stats.record_page(url, "cat"))
        for html in [b"", "<p></p>", "<script>text</script>"]:
            self.assertFalse(self.stats.record_page("https://cs.uci.edu/", html))
        self.assertEqual(self.stats.snapshot()["unique_pages"], 0)

    def test_resume_does_not_double_count(self):
        self.stats.record_page("https://ics.uci.edu/", "cat cat")
        self.stats.close()
        self.stats = Analytics(self.path)
        self.assertFalse(self.stats.record_page("https://ics.uci.edu/#again", "cat cat"))
        self.assertEqual(self.stats.snapshot()["top_words"], [("cat", 2)])

    def response(self, url="https://cs.uci.edu/final", status=200, media="text/html"):
        return SimpleNamespace(status=status, url=url, raw_response=SimpleNamespace(
            url=url, content=b"<p>cat</p>", headers={"Content-Type": media}))

    def test_response_redirect_uses_final_url(self):
        self.assertTrue(self.stats.record_response("https://ics.uci.edu/start", self.response()))
        self.assertEqual(self.stats.snapshot()["longest_page"][0], "https://cs.uci.edu/final")
        self.assertFalse(self.stats.record_response("https://cs.uci.edu/start",
                                                   self.response(url="https://evil.org/")))

    def test_response_errors_and_non_html(self):
        for resp in [self.response(status=404), self.response(media="application/pdf"),
                     SimpleNamespace(status=200, raw_response=None)]:
            self.assertFalse(self.stats.record_response("https://cs.uci.edu/", resp))

    def test_transaction_rolls_back_after_word_write_failure(self):
        # Simulate a storage error between the page insert and frequency updates.
        self.stats._db.execute("CREATE TRIGGER fail_words BEFORE INSERT ON words "
                               "BEGIN SELECT RAISE(ABORT, 'simulated failure'); END")
        with self.assertRaises(Exception):
            self.stats.record_page("https://cs.uci.edu/", "cat")
        self.assertEqual(self.stats.snapshot()["unique_pages"], 0)
        self.stats._db.execute("DROP TRIGGER fail_words")
        self.assertTrue(self.stats.record_page("https://cs.uci.edu/", "cat"))

    def test_threaded_replays(self):
        with ThreadPoolExecutor(max_workers=4) as workers:
            list(workers.map(lambda i: self.stats.record_page(
                "https://cs.uci.edu/%d" % (i % 5), "cat"), range(100)))
        self.assertEqual(self.stats.snapshot()["unique_pages"], 5)
        self.assertEqual(self.stats.snapshot()["top_words"], [("cat", 5)])

    def test_report_empty_and_populated(self):
        report = Path(self.temp.name) / "report.txt"
        self.stats.write_report(report)
        self.assertIn("No pages recorded.", report.read_text())
        self.stats.record_page("https://vision.ics.uci.edu/", "cat cat")
        self.stats.write_report(report)
        text = report.read_text()
        self.assertIn("Unique pages: 1", text)
        self.assertIn("http://vision.ics.uci.edu, 1", text)
        self.assertIn("cat, 2", text)


if __name__ == "__main__":
    unittest.main()
