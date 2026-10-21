# Part C: persistent crawl analytics

## Files and interface

analytics.py supplies Analytics.record_page(url, html) and
record_response(requested_url, resp). The minimal hook in scraper.scraper()
records a response before link extraction. This commit contains Part C only;
link extraction, trap wiring, and launcher integration remain team integration
work. The local integrated crawler has been tested separately.

## Counting rules

- URL identity discards only the fragment. Queries, schemes, and trailing
  slashes remain distinct. Identical content at different URLs counts separately.
- Successful nonempty HTML responses in the four assignment domains are counted.
  Redirected content belongs to the final response URL; external redirects are
  excluded. Explicit non-HTML types and responses without text are skipped.
- Strip markup, comments, head, scripts, styles, templates, and noscript. Tokens
  are lowercase ASCII letter/digit runs retaining internal apostrophes.
- Longest-page word counts include stopwords. Corpus top 50 excludes the fixed
  English STOP_WORDS set and sorts by frequency, then alphabetically for ties.
- ICS subdomain rows sort alphabetically. HTTP and HTTPS pages share a hostname
  count; the apex itself is not a subdomain. Report http:// prefixes are labels.
- Each page and its frequencies commit atomically to SQLite. Resume/replay does
  not double-count. Record before content-similarity rejection.

## Test and export

From the project directory, with the assignment dependencies installed:

    python -B -m unittest -v test_analytics
    python analytics.py --db frontier.analytics.sqlite3 --report frontier.report.txt

The module creates its default database lazily. Export reads saved statistics
and performs no network requests. A report generated during a crawl is a
consistent snapshot. The caller may use Analytics(custom_path) for separate
crawl runs. Stop crawling before moving a database to start a fresh run; the
base launcher's --restart flag does not reset Part C by itself.

The frontier in the team baseline merges URL schemes/trailing slashes. Coordinate
the integration fix before the real crawl so all assignment-distinct URLs can
reach analytics. No actual crawl results are included in this commit.

13 offline tests cover URL identity, duplicate text, stopwords, longest page,
subdomains, top-50 ordering, redirects, response filtering, durable resume,
concurrent replays, report generation, and transaction rollback.
