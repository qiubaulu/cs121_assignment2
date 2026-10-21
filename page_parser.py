"""Part B: response checking and text extraction. This module never downloads pages.

parse_page(url, resp) turns the cache server's Response into one ParsedPage that the other parts can use directly



"""





import logging
import re
from urllib.parse import urljoin, urldefrag, urlparse
 
from bs4 import BeautifulSoup, UnicodeDammit
 
from trap_detector import is_dead_page


logging.getLogger("bs4.dammit").setLevel(logging.ERROR)
# -----------------------------------------------------statuses---------------------
# 10 种处理结果
OK = "OK"
REDIRECT = "REDIRECT"
HTTP_ERROR = "HTTP_ERROR"
CACHE_ERROR = "CACHE_ERROR"
NO_RESPONSE = "NO_RESPONSE"
OUT_OF_SCOPE = "OUT_OF_SCOPE"
NOT_HTML = "NOT_HTML"
TOO_LARGE = "TOO_LARGE"
EMPTY = "EMPTY"
PARSE_ERROR = "PARSE_ERROR"

#------------------------------------------------------setting-----------------------


# only 4 is valid
ALLOWED_DOMAINS = ("ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu")

HTML_TYPES = ("text/html", "application/xhtml+xml")
# safity cap, incase a gigantic page
MAX_PARSE_BYTES = 10 * 1024 * 1024
# Elements whose text is not page content. 
NON_CONTENT_TAGS = ["script", "style", "noscript", "template", "head"]

WORD_PATTERN = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)*")


# output
class ParsedPage(object):
    """Everything later stages need to know about one downloaded page."""
 
    __slots__ = ("requested_url", "final_url", "http_status", "status", "reason",
                 "html", "text", "words", "content_type", "content_length",
                 "redirect_target")
 
    def __init__(self, requested_url, final_url=None, http_status=None,
                 status=NO_RESPONSE, reason=""):
        self.requested_url = requested_url
        self.final_url = final_url or requested_url
        self.http_status = http_status
        self.status = status
        self.reason = reason
        self.html = ""
        self.text = ""
        self.words = []
        self.content_type = ""
        self.content_length = 0
        self.redirect_target = None
 
    @property
    def ok(self):
        """True when the page is usable: index it and (if Part D agrees) expand it."""
        return self.status == OK
 
    def __repr__(self):
        return "ParsedPage(status={}, http={}, final_url={!r}, words={}, reason={!r})".format(
            self.status, self.http_status, self.final_url, len(self.words), self.reason)
 

#--------------------------------------------------------------------helpers-------------

def _header(raw, name):
    """Read a response header without crashing on odd raw_response objects."""
    headers = getattr(raw, "headers", None) or {}
    try:
        return headers.get(name) or ""
    except AttributeError:
        return ""
 
def in_allowed_domains(url):
    """True if url is http(s) on one of the four domains or their subdomains.

    """
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
    except (TypeError, ValueError):
        return False
    if parsed.scheme not in ("http", "https") or not host:
        return False

    return any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS)
 


def _media_type(content_type_header):
    
    return content_type_header.split(";", 1)[0].strip().lower()



def _content_length(raw, content):
    """计算大小	
    有正文就直接量正文的长度，没有就读 Content-Length 
    """
    if content:
        return len(content)
    try:
        return int(_header(raw, "Content-Length"))
    except (TypeError, ValueError):
        return 0

def decode_html(content):
    """Bytes -> str
 
    """
    if isinstance(content, str):
        return content
    dammit = UnicodeDammit(content, is_html=True)
    if dammit.unicode_markup is not None:
        return dammit.unicode_markup
    return content.decode("utf-8", errors="replace")

def extract_text(html):
    """Visible text of an HTML page (markup, scripts, styles, <head> removed).
    先删掉 script、style、head 这些标签，再取出剩下的文字

    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(NON_CONTENT_TAGS):
        tag.decompose()
    return soup.get_text(" ", strip=True)
 
 
def tokenize(text):
    #return WORD_PATTERN.findall(text.lower().replace("’", "'"))
    return WORD_PATTERN.findall(text.lower().replace("\u2019", "'"))


#------------------------------------------------------------ parse_page

def parse_page(url, resp):
    """Check a Response and extract what the other parts need"""
    if resp is None:
        return ParsedPage(url, reason="no response object")
 
    status_code =getattr(resp, "status", None)
    raw = getattr(resp, "raw_response", None) 

    # The cache follows redirects; raw.url is where the content actually came from.
    final_url = (getattr(raw, "url", None) or getattr(resp, "url", None) or url)
    final_url = urldefrag(final_url)[0]
    page = ParsedPage(url, final_url, status_code)


    # 1. Cache-server errors (600-608) come with an explanation in resp.error.
    if isinstance(status_code, int) and status_code >= 600:
        page.status = CACHE_ERROR
        page.reason = str(getattr(resp, "error", "") or "cache server error")
        return page
    if raw is None:
        page.status = NO_RESPONSE
        page.reason = str(getattr(resp, "error", "") or "no raw_response")
        return page
 
    page.content_type = _media_type(_header(raw, "Content-Type"))
    content = getattr(raw, "content", None) or b""
    page.content_length = _content_length(raw, content)



    # 2. A redirect the cache did not follow: hand the target back to the crawler.
    if isinstance(status_code, int) and 300 <= status_code < 400:
        location = _header(raw, "Location").strip()
        if location:
            page.redirect_target = urldefrag(urljoin(final_url, location))[0]
            page.status = REDIRECT
            page.reason = "redirects to " + page.redirect_target
        else:
            page.status = HTTP_ERROR
            page.reason = "{} redirect without Location header".format(status_code)
        return page


    # 3. Anything else that is not 200
    if status_code != 200:
        page.status = HTTP_ERROR
        page.reason = "HTTP {}".format(status_code)
        return page

    # 4. if not in the allowed domains: do not index it
    if not in_allowed_domains(final_url):
        page.status = OUT_OF_SCOPE
        page.reason = "redirected outside the allowed domains to " + final_url
        return page

    # 5. Not HTML 
    if page.content_type and page.content_type not in HTML_TYPES:
        page.status = NOT_HTML
        page.reason = "content type " + page.content_type
        return page

    # 6. too big for a page
    if page.content_length > MAX_PARSE_BYTES:
        page.status = TOO_LARGE
        page.reason = "{} bytes > {}".format(page.content_length, MAX_PARSE_BYTES)
        return page

    # 7. Decode and pull out the visible text
    try:
        html = decode_html(content)
        text = extract_text(html) if html.strip() else ""
    except Exception as e:                    
        # broken markup must not kill a worker
        page.status = PARSE_ERROR
        page.reason = "could not parse HTML: {!r}".format(e)
        return page
    # 8. Dead page: 200 but no body or no visible text (Part D's rule).
    if is_dead_page(200, content, text):
        page.status = EMPTY
        page.reason = "200 with no body" if not content.strip() else "200 with no visible text"
        return page
    

    page.status = OK
    page.html = html
    page.text = text
    page.words = tokenize(text)
    page.reason = "{} words".format(len(page.words))
    return page