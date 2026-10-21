import unittest
from trap_detector import (
    has_repeated_pattern,
    is_trap,
    get_url_pattern,
    URLHistory,
    is_low_information,
    content_similarity,
    ContentHistory,
    is_dead_page,
    is_large_file
)


class TestTrapDetector(unittest.TestCase):

    # --------------------------------------------------
    # 1. has_repeated_pattern()
    # Tests repeated URL path segments
    # --------------------------------------------------

    def test_repeated_pattern_function(self):
        segments = ["a", "b", "a", "b", "a", "b"]
        self.assertTrue(has_repeated_pattern(segments))

    def test_non_repeated_pattern_function(self):
        segments = ["a", "b", "c", "d"]
        self.assertFalse(has_repeated_pattern(segments))

    # --------------------------------------------------
    # 2. is_trap()
    # Tests URL depth and repeated path patterns
    # --------------------------------------------------

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

    # --------------------------------------------------
    # 3. get_url_pattern()
    # Tests URL family identification
    # --------------------------------------------------

    def test_same_url_pattern(self):
        url1 = "https://www.ics.uci.edu/calendar?page=1"
        url2 = "https://www.ics.uci.edu/calendar?page=200"

        self.assertEqual(
            get_url_pattern(url1),
            get_url_pattern(url2)
        )

    def test_different_url_pattern(self):
        url1 = "https://www.ics.uci.edu/calendar?page=1"
        url2 = "https://www.ics.uci.edu/news?page=1"

        self.assertNotEqual(
            get_url_pattern(url1),
            get_url_pattern(url2)
        )

    def test_query_parameter_order(self):
        url1 = "https://www.ics.uci.edu/search?page=1&year=2026"
        url2 = "https://www.ics.uci.edu/search?year=2025&page=2"

        self.assertEqual(
            get_url_pattern(url1),
            get_url_pattern(url2)
        )

    def test_blank_query_parameter(self):
        url1 = "https://www.ics.uci.edu/search?page="
        url2 = "https://www.ics.uci.edu/search?page=10"

        self.assertEqual(
            get_url_pattern(url1),
            get_url_pattern(url2)
        )

    # --------------------------------------------------
    # 4. URLHistory
    # Tests URL family thresholds and duplicate tracking
    # --------------------------------------------------

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

    # --------------------------------------------------
    # 5. is_low_information()
    # Tests word count and unique word ratio
    # --------------------------------------------------

    def test_empty_content(self):
        self.assertTrue(is_low_information(""))

    def test_whitespace_content(self):
        self.assertTrue(is_low_information("   "))

    def test_short_content(self):
        self.assertTrue(is_low_information("No results found"))

    def test_normal_content(self):
        text = " ".join(f"word{i}" for i in range(50))
        self.assertFalse(is_low_information(text))

    def test_repetitive_content(self):
        text = "hello " * 100
        self.assertTrue(is_low_information(text))

    def test_word_count_boundary(self):
        text = " ".join(f"word{i}" for i in range(30))
        self.assertFalse(is_low_information(text))

    def test_unique_ratio_boundary(self):
        text = " ".join(f"word{i % 6}" for i in range(30))
        self.assertFalse(is_low_information(text))

    # --------------------------------------------------
    # 6. content_similarity()
    # Tests Jaccard similarity between two texts
    # --------------------------------------------------

    def test_identical_content(self):
        text1 = "apple banana orange"
        text2 = "apple banana orange"

        self.assertEqual(content_similarity(text1, text2), 1.0)

    def test_completely_different_content(self):
        text1 = "apple banana"
        text2 = "orange grape"

        self.assertEqual(content_similarity(text1, text2), 0.0)

    def test_partially_similar_content(self):
        text1 = "apple banana orange"
        text2 = "apple banana grape"

        self.assertAlmostEqual(
            content_similarity(text1, text2),
            0.5
        )

    def test_case_insensitive_content(self):
        text1 = "Apple BANANA"
        text2 = "apple banana"

        self.assertEqual(content_similarity(text1, text2), 1.0)

    def test_both_empty_content(self):
        self.assertEqual(content_similarity("", ""), 1.0)

    def test_one_empty_content(self):
        self.assertEqual(content_similarity("apple banana", ""), 0.0)

    # --------------------------------------------------
    # 7. ContentHistory
    # Tests page similarity, URL caching and family repetition
    # --------------------------------------------------

    def test_content_history_first_page(self):
        history = ContentHistory()
        url = "https://www.ics.uci.edu/calendar?page=1"

        self.assertFalse(
            history.is_similar(url, "apple banana orange")
        )

    def test_content_history_identical(self):
        history = ContentHistory()

        url1 = "https://www.ics.uci.edu/calendar?page=1"
        url2 = "https://www.ics.uci.edu/calendar?page=2"

        history.is_similar(url1, "apple banana orange")

        self.assertTrue(
            history.is_similar(url2, "apple banana orange")
        )

    def test_content_history_different(self):
        history = ContentHistory()

        url1 = "https://www.ics.uci.edu/calendar?page=1"
        url2 = "https://www.ics.uci.edu/calendar?page=2"

        history.is_similar(url1, "apple banana orange")

        self.assertFalse(
            history.is_similar(url2, "cat dog elephant")
        )

    def test_content_history_threshold(self):
        history = ContentHistory(threshold=0.5)

        url1 = "https://www.ics.uci.edu/calendar?page=1"
        url2 = "https://www.ics.uci.edu/calendar?page=2"

        history.is_similar(url1, "apple banana orange")

        self.assertTrue(
            history.is_similar(url2, "apple banana grape")
        )

    def test_content_history_different_families(self):
        history = ContentHistory()

        url1 = "https://www.ics.uci.edu/calendar?page=1"
        url2 = "https://www.ics.uci.edu/news?page=1"

        history.is_similar(url1, "apple banana orange")

        self.assertFalse(
            history.is_similar(url2, "apple banana orange")
        )

    def test_repetitive_family(self):
        history = ContentHistory(repeat_threshold=3)

        for page in range(1, 5):
            url = f"https://www.ics.uci.edu/calendar?page={page}"
            history.is_similar(url, "No results found")

        self.assertTrue(
            history.is_repetitive_family(
                "https://www.ics.uci.edu/calendar?page=5"
            )
        )

    def test_same_url_not_counted_twice(self):
        history = ContentHistory()
        url = "https://www.ics.uci.edu/calendar?page=1"

        history.is_similar(url, "apple banana orange")
        history.is_similar(url, "apple banana orange")

        pattern = get_url_pattern(url)

        self.assertEqual(history.repeated[pattern], 0)
        self.assertEqual(len(history.seen_urls), 1)

    def test_duplicate_content_different_urls(self):
        history = ContentHistory()

        url1 = "https://www.ics.uci.edu/calendar?page=1"
        url2 = "https://www.ics.uci.edu/calendar?page=2"

        history.is_similar(url1, "apple banana orange")
        history.is_similar(url2, "apple banana orange")

        pattern = get_url_pattern(url1)

        self.assertEqual(history.repeated[pattern], 1)

    def test_cached_similarity_result(self):
        history = ContentHistory()

        url1 = "https://www.ics.uci.edu/page?id=1"
        url2 = "https://www.ics.uci.edu/page?id=2"

        history.is_similar(url1, "apple banana orange")

        self.assertTrue(
            history.is_similar(url2, "apple banana orange")
        )

        self.assertTrue(
            history.is_similar(url2, "apple banana orange")
        )

        pattern = get_url_pattern(url2)

        self.assertEqual(history.repeated[pattern], 1)

    def test_cached_non_similar_page(self):
        history = ContentHistory()

        url = "https://www.ics.uci.edu/page?id=1"
        text = "apple banana orange"

        self.assertFalse(history.is_similar(url, text))
        self.assertFalse(history.is_similar(url, text))

        pattern = get_url_pattern(url)

        self.assertEqual(len(history.history[pattern]), 1)
        self.assertEqual(history.repeated[pattern], 0)
        self.assertFalse(history.seen_urls[url])

    # --------------------------------------------------
    # 8. is_dead_page()
    # Tests empty responses with HTTP 200 status
    # --------------------------------------------------

    def test_dead_empty_response(self):
        self.assertTrue(is_dead_page(200, b"", ""))

    def test_dead_empty_text(self):
        content = b"<html><body></body></html>"
        self.assertTrue(is_dead_page(200, content, ""))

    def test_normal_page(self):
        content = b"<html><body>Hello UCI</body></html>"
        self.assertFalse(is_dead_page(200, content, "Hello UCI"))

    def test_other_status(self):
        self.assertFalse(is_dead_page(404, b"", ""))

    # --------------------------------------------------
    # 9. is_large_file()
    # Tests file size and content type filtering
    # --------------------------------------------------

    def test_small_file(self):
        self.assertFalse(is_large_file(1024, "application/pdf"))

    def test_large_binary_file(self):
        size = 10 * 1024 * 1024
        self.assertTrue(is_large_file(size, "application/zip"))

    def test_large_html(self):
        size = 10 * 1024 * 1024
        self.assertFalse(is_large_file(size, "text/html"))

    def test_unknown_size(self):
        self.assertFalse(is_large_file(None, "application/zip"))

    def test_size_boundary(self):
        size = 5 * 1024 * 1024
        self.assertFalse(is_large_file(size, "application/pdf"))


if __name__ == "__main__":
    unittest.main()
