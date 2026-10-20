
import unittest
from trap_detector import (
    is_trap,
    has_repeated_pattern,
    get_url_pattern,
    URLHistory
)


class TestTrapDetector(unittest.TestCase):

    def test_normal_url(self):
        url = "https://www.ics.uci.edu/about"
        self.assertFalse(is_trap(url))

    def test_deep_url(self):
        url = "https://www.ics.uci.edu/a/b/c/d/e/f/g/h/i/j/k"
        self.assertTrue(is_trap(url))

    def test_repeated_single_segment(self):
        url = "https://www.ics.uci.edu/a/a/a/a"
        self.assertTrue(is_trap(url))

    def test_repeated_two_segments(self):
        url = "https://www.ics.uci.edu/a/b/a/b"
        self.assertFalse(is_trap(url))

    def test_repeated_three_times(self):
        url = "https://www.ics.uci.edu/a/b/a/b/a/b"
        self.assertTrue(is_trap(url))

    def test_repeated_three_segments(self):
        url = "https://www.ics.uci.edu/a/b/c/a/b/c"
        self.assertFalse(is_trap(url))

    def test_three_segments_three_times(self):
        url = "https://www.ics.uci.edu/a/b/c/a/b/c/a/b/c"
        self.assertTrue(is_trap(url))

    def test_incomplete_repetition(self):
        url = "https://www.ics.uci.edu/a/b/c/a/b"
        self.assertFalse(is_trap(url))

    def test_no_repetition(self):
        url = "https://www.ics.uci.edu/a/b/c/d/e"
        self.assertFalse(is_trap(url))

    def test_repetition_in_middle(self):
        url = "https://www.ics.uci.edu/x/a/b/a/b/a/b/y"
        self.assertTrue(is_trap(url))

    def test_same_url_pattern(self):
        url1 = "https://www.ics.uci.edu/calendar?page=1"
        url2 = "https://www.ics.uci.edu/calendar?page=200"
        self.assertEqual(get_url_pattern(url1), get_url_pattern(url2))

    def test_different_url_pattern(self):
        url1 = "https://www.ics.uci.edu/calendar?page=1"
        url2 = "https://www.ics.uci.edu/news?page=1"
        self.assertNotEqual(get_url_pattern(url1), get_url_pattern(url2))

    def test_history_threshold(self):
        history = URLHistory(threshold=3)

        for page in range(1, 4):
            url = f"https://www.ics.uci.edu/calendar?page={page}"
            self.assertFalse(history.is_suspicious(url))

        url = "https://www.ics.uci.edu/calendar?page=4"
        self.assertTrue(history.is_suspicious(url))

    def test_duplicate_url(self):
        history = URLHistory(threshold=3)
        url = "https://www.ics.uci.edu/calendar?page=1"

        for _ in range(5):
            self.assertFalse(history.is_suspicious(url))

        self.assertEqual(
            len(history.history[get_url_pattern(url)]),
            1
        )

    def test_duplicate_after_threshold(self):
        history = URLHistory(threshold=2)

        for page in range(1, 4):
            url = f"https://www.ics.uci.edu/calendar?page={page}"
            history.is_suspicious(url)

        old_url = "https://www.ics.uci.edu/calendar?page=1"
        self.assertTrue(history.is_suspicious(old_url))

    def test_different_families(self):
        history = URLHistory(threshold=1)

        url1 = "https://www.ics.uci.edu/calendar?page=1"
        url2 = "https://www.ics.uci.edu/news?page=1"

        self.assertFalse(history.is_suspicious(url1))
        self.assertFalse(history.is_suspicious(url2))

    def test_query_parameter_order(self):
        url1 = "https://www.ics.uci.edu/search?page=1&year=2026"
        url2 = "https://www.ics.uci.edu/search?year=2025&page=2"

        self.assertEqual(get_url_pattern(url1), get_url_pattern(url2))

    def test_blank_query_parameter(self):
        url1 = "https://www.ics.uci.edu/search?page="
        url2 = "https://www.ics.uci.edu/search?page=10"

        self.assertEqual(get_url_pattern(url1), get_url_pattern(url2))


if __name__ == "__main__":
    unittest.main()
