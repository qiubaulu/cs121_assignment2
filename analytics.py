"""Part C: durable crawl statistics. This module never downloads pages.

Run `python analytics.py --report report.txt` to export an existing crawl.
"""

import argparse
from collections import Counter
from pathlib import Path
import re
import sqlite3
from threading import RLock
from urllib.parse import urldefrag, urlparse

from bs4 import BeautifulSoup


# Explicit, fixed English stopword list: no network downloads or NLTK data.
STOP_WORDS = frozenset("""
a about above after again against all am an and any are aren't as at be because
been before being below between both but by can can't cannot could couldn't did
didn't do does doesn't doing don't down during each few for from further had
hadn't has hasn't have haven't having he he'd he'll he's her here here's hers
herself him himself his how how's i i'd i'll i'm i've if in into is isn't it it's
its itself let's me more most mustn't my myself no nor not of off on once only or
other ought our ours ourselves out over own same shan't she she'd she'll she's
should shouldn't so some such than that that's the their theirs them themselves
then there there's these they they'd they'll they're they've this those through
to too under until up very was wasn't we we'd we'll we're we've were weren't
what what's when when's where where's which while who who's whom why why's with
won't would wouldn't you you'd you'll you're you've your yours yourself yourselves
also just now s t d ll m o re ve don doesn didn isn aren wasn weren hasn haven
hadn shouldn wouldn couldn won shan mustn needn mightn ain
""".split())

# ASCII letter/digit runs, with contractions kept together (e.g. "don't").
WORD_PATTERN = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)*")
ALLOWED_DOMAINS = ("ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu")
DEFAULT_DB = "frontier.analytics.sqlite3"


def page_identity(url):
    """Only discard the fragment; preserve queries, paths, and HTTP vs HTTPS."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        if parsed.scheme not in ("http", "https") or not host:
            return None
        if not any(host == domain or host.endswith("." + domain)
                   for domain in ALLOWED_DOMAINS):
            return None
        return urldefrag(url)[0]
    except (TypeError, ValueError, AttributeError):
        return None


def visible_words(html):
    """Exclude markup and non-content elements; count stopwords for page length."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "head"]):
        tag.decompose()
    return WORD_PATTERN.findall(soup.get_text(" ", strip=True).lower().replace("’", "'"))


class Analytics:
    """One connection per instance; share an instance between crawler threads.

    A page and its word frequencies commit together. Replayed URLs after a
    crawler restart do not double-count. Distinct URLs with identical text do.
    """

    def __init__(self, db_path=DEFAULT_DB):
        self._lock = RLock()
        self._db = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30)
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS pages (
                url TEXT PRIMARY KEY, host TEXT NOT NULL, word_count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS words (
                word TEXT PRIMARY KEY, frequency INTEGER NOT NULL
            );
        """)

    def record_page(self, url, html):
        """Record a successfully fetched HTML page. Return True only if new.

        Call this before content-similarity rejection so distinct URLs retain
        their assignment-defined uniqueness. Empty text is not a valid page.
        """
        identity = page_identity(url)
        if identity is None or not html:
            return False
        tokens = visible_words(html)
        if not tokens:
            return False
        counts = Counter(word for word in tokens if word not in STOP_WORDS)
        with self._lock, self._db:
            result = self._db.execute(
                "INSERT OR IGNORE INTO pages VALUES (?, ?, ?)",
                (identity, urlparse(identity).hostname, len(tokens)))
            if result.rowcount == 0:
                return False
            # Avoid requiring a recent SQLite UPSERT implementation.
            self._db.executemany("INSERT OR IGNORE INTO words VALUES (?, 0)",
                                 ((word,) for word in counts))
            self._db.executemany(
                "UPDATE words SET frequency = frequency + ? WHERE word = ?",
                ((count, word) for word, count in counts.items()))
        return True

    def record_response(self, requested_url, resp):
        """Accept the existing utils.response.Response interface (no requests).

        Attribute content to the final response URL when redirected. Do not
        index successful redirects outside the four assignment domains.
        """
        raw = getattr(resp, "raw_response", None)
        if getattr(resp, "status", None) != 200 or raw is None:
            return False
        content_type = getattr(raw, "headers", {}).get("Content-Type", "")
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type and media_type not in ("text/html", "application/xhtml+xml"):
            return False
        final_url = (getattr(raw, "url", None) or getattr(resp, "url", None)
                     or requested_url)
        return self.record_page(final_url, getattr(raw, "content", b""))

    def snapshot(self):
        """Return deterministic, report-ready values from one database snapshot."""
        with self._lock, self._db:
            # Explicit read transaction also protects against another writer.
            self._db.execute("BEGIN")
            total = self._db.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
            longest = self._db.execute(
                "SELECT url, word_count FROM pages ORDER BY word_count DESC, url LIMIT 1"
            ).fetchone()
            top = self._db.execute(
                "SELECT word, frequency FROM words ORDER BY frequency DESC, word LIMIT 50"
            ).fetchall()
            subdomains = self._db.execute(
                "SELECT host, COUNT(*) FROM pages WHERE host LIKE '%.ics.uci.edu' "
                "GROUP BY host ORDER BY host"
            ).fetchall()
        return {"unique_pages": total, "longest_page": longest,
                "top_words": top, "ics_subdomains": subdomains}

    def write_report(self, path="frontier.report.txt"):
        data = self.snapshot()
        longest = data["longest_page"]
        lines = ["Assignment 2 - Crawl Analytics", "",
                 "1. Unique pages: {}".format(data["unique_pages"]), "",
                 "2. Longest page (including stopwords):"]
        lines.append("{}, {} words".format(*longest) if longest else "No pages recorded.")
        lines += ["", "3. Top 50 words (excluding English stopwords):"]
        lines += ["{}, {}".format(*item) for item in data["top_words"]]
        lines += ["", "4. ICS subdomains: {}".format(len(data["ics_subdomains"]))]
        lines += ["http://{}, {}".format(*item) for item in data["ics_subdomains"]]
        lines += ["", "Counting rules:",
                  "Successful, nonempty HTML pages; identity is the final URL without fragment.",
                  "Query strings and HTTP/HTTPS remain distinct; equal text is not deduplicated.",
                  "Words: lowercase ASCII letter/digit runs, retaining internal apostrophes.",
                  "Stopwords: fixed STOP_WORDS list in analytics.py; page length includes them.",
                  "ICS root pages contribute to totals, but are not themselves a subdomain.",
                  "Subdomain http:// prefixes are display labels; counts combine both schemes."]
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return data

    def close(self):
        with self._lock:
            self._db.close()


# Lazy initialization: importing the scraper must not create or erase crawl data.
_default = None
_default_lock = RLock()


def record_response(url, resp):
    global _default
    with _default_lock:
        if _default is None:
            _default = Analytics()
    return _default.record_response(url, resp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--report", default="frontier.report.txt")
    args = parser.parse_args()
    if not Path(args.db).is_file():
        parser.error("No analytics database found. Crawl first or select --db.")
    analytics = Analytics(args.db)
    try:
        analytics.write_report(args.report)
    finally:
        analytics.close()
    print("Report written to {}".format(args.report))


if __name__ == "__main__":
    main()
