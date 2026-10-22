from urllib.parse import urlparse, parse_qsl

def has_repeated_pattern(segments):
    n = len(segments)

    for i in range(n):
        for j in range(i + 1, n):
            if segments[i] != segments[j]:
                continue

            size = j - i

            if j + 2 * size > n:
                continue

            first = segments[i:j]
            second = segments[j:j + size]
            third = segments[j + size:j + 2 * size]

            if first == second == third:
                return True

    return False


def is_trap(url):
    parsed = urlparse(url)
    segments = [part for part in parsed.path.split("/") if part]

    if len(segments) > 10:
        return True

    if has_repeated_pattern(segments):
        return True

    return False


def get_url_pattern(url):
    parsed = urlparse(url)
    params = parse_qsl(parsed.query, keep_blank_values=True)

    keys = tuple(sorted(set(key for key, value in params)))

    return (parsed.netloc.lower(), parsed.path, keys)


class URLHistory:

    def __init__(self, threshold=50):
        self.threshold = threshold
        self.history = {}

    def is_suspicious(self, url):
        pattern = get_url_pattern(url)

        if pattern not in self.history:
            self.history[pattern] = set()

        if url not in self.history[pattern]:
            self.history[pattern].add(url)

        return len(self.history[pattern]) > self.threshold


def is_low_information(text, min_words=30, min_ratio=0.2):
    if not text or not text.strip():
        return True

    words = text.lower().split()

    if len(words) < min_words:
        return True

    unique_words = set(words)
    ratio = len(unique_words) / len(words)

    if ratio < min_ratio:
        return True

    return False


def content_similarity(text1, text2):
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 and not words2:
        return 1.0

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)




class ContentHistory:

    def __init__(self, threshold=0.9, repeat_threshold=3):
        self.threshold = threshold
        self.repeat_threshold = repeat_threshold
        self.history = {}
        self.repeated = {}
        self.seen_urls = {}

    def is_similar(self, url, text):
        if url in self.seen_urls:
            return self.seen_urls[url]

        pattern = get_url_pattern(url)

        if pattern not in self.history:
            self.history[pattern] = []
            self.repeated[pattern] = 0

        for old_text in self.history[pattern]:
            similarity = content_similarity(text, old_text)

            if similarity >= self.threshold:
                self.repeated[pattern] += 1
                self.seen_urls[url] = True
                return True

        self.history[pattern].append(text)
        self.seen_urls[url] = False
        return False

    def is_repetitive_family(self, url):
        pattern = get_url_pattern(url)

        return self.repeated.get(pattern, 0) >= self.repeat_threshold

def is_dead_page(status, content, text):
    if status != 200:
        return False

    if not content:
        return True

    if not text or not text.strip():
        return True

    return False


def is_large_file(content_size, content_type="", max_size=5 * 1024 * 1024):
    if content_size is None:
        return False

    if content_size <= max_size:
        return False

    content_type = content_type.lower()

    if "text/html" in content_type:
        return False

    return True


class TrapDetector:

    def __init__(self):
        self.url_history = URLHistory()
        self.content_history = ContentHistory()

    def should_crawl(self, url):
        if is_trap(url):
            return False

        self.url_history.is_suspicious(url)
        return True

    def should_expand(self, url, status, content, text,
                      content_type="text/html"):
        if status != 200:
            return False

        if is_dead_page(status, content, text):
            return False

        if is_large_file(len(content), content_type):
            return False

        suspicious = self.url_history.is_suspicious(url)
        similar = self.content_history.is_similar(url, text)
        repetitive = self.content_history.is_repetitive_family(url)
        low_info = is_low_information(text)

        if suspicious and similar and repetitive and low_info:
            return False

        return True


