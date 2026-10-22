
Part B: response checking and text extraction

    page_parser.py supplies parse_page(url, resp) -> ParsedPage, every outcome is 
    described by page.status plus a short page.reason for the logs.

-----------------------------------------------------------------------------------------------

how to use it:

from page_parser import parse_page
from url_utils import get_links

page = parse_page(url, resp)
if page.redirect_target:          # 3xx the cache did not follow
    links = [page.redirect_target]
elif page.ok:                     # Part D decides whether to expand
    links = get_links(page.final_url, page.html)   # Part A, relative to the final URL
else:
    links = []

--------------------------------------------------------------------------------------------------




ParsedPage fields
    requested_url   the URL taken from the frontier
    final_url       where the content really came from (after redirects), no fragment
    http_status     status code from the cache server (int, or None)
    status          processing status, one of the constants below
    reason          short human-readable explanation (useful in logs)
    html            decoded HTML as str ("" unless status is OK)
    text            visible text, markup/scripts/styles removed ("" unless OK)
    words           lowercase tokens, same rules as analytics.py ([] unless OK)
    content_type    media type, e.g. "text/html" ("" if the server sent none)
    content_length  size of the body in bytes (header value, else real size)
    redirect_target absolute URL to follow for an unfollowed 3xx, else None


Processing statuses (page.status)
    OK            200, HTML, in scope, has visible text -> index it and expand links
    REDIRECT      3xx with a Location header -> crawl redirect_target instead
    HTTP_ERROR    4xx / 5xx (or another non-200 HTTP code)
    CACHE_ERROR   600-608: the cache server refused/failed (see reason)
    NO_RESPONSE   no raw_response at all
    OUT_OF_SCOPE  redirected to a URL outside the four allowed domains
    NOT_HTML      PDF, image, zip, ... served under an HTML-looking URL
    TOO_LARGE     body bigger than MAX_PARSE_BYTES (not worth parsing)
    EMPTY         200 but no body / no visible text (dead page)
    PARSE_ERROR   the HTML could not be decoded or parsed

