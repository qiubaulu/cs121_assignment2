
from urllib.parse import urlparse, parse_qsl


def has_repeated_pattern(segments):
    n = len(segments)

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

from urllib.parse import parse_qsl


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
