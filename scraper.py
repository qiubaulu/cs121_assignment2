import logging

from analytics import record_response
from page_parser import parse_page, REDIRECT
from trap_detector import TrapDetector
from url_utils import get_links, is_valid


logger = logging.getLogger(__name__)

detector = TrapDetector()


def scraper(url, resp):
    record_response(url, resp)

    links = extract_next_links(url, resp)

    return [link for link in links if is_valid(link)]


def extract_next_links(url, resp):
    page = parse_page(url, resp)

    if page.status == REDIRECT:
        target = page.redirect_target

        if target and is_valid(target):
            if detector.should_crawl(target):
                return [target]

        return []

    if not page.ok:
        logger.debug(
            "Skipping %s: %s (%s)",
            url,
            page.status,
            page.reason
        )
        return []

    raw = getattr(resp, "raw_response", None)
    content = getattr(raw, "content", None) or b""

    final_url = page.final_url

    if not detector.should_expand(
        final_url,
        page.http_status,
        content,
        page.text,
        page.content_type
    ):
        return []

    links = get_links(final_url, page.html)

    return [
        link for link in links
        if detector.should_crawl(link)
    ]