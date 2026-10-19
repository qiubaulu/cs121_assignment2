#url_utils.py is used to extract links from web page HTML, complete the URLs, remove the “#”, and encode special characters, then filter out the links that are allowed to be accessed.
#is_valid(url): Checks if the protocol is HTTP/HTTPS, checks if the domain is within the allowed range, and checks if the path corresponds to a blocked. Returns True if all checks pass. Returns False if any check fails.
#get_links(page_url, html): Extracts links from the <a> tags in the HTML, organizes and filters the results using is_valid(), then removes duplicate URLs from the returned list.
#The call should provide “page_url”: the full URL of the current page and html: The HTML content of this page.
#Returns a list containing the allowed addresses. If no addresses meet the requirements, it returns an empty list.
#For example: 
#from url_utils import get_links
#links = get_links(page_url, html)
#Need to install BeautifulSoup 4

from urllib.parse import urlparse, urljoin, quote
from bs4 import BeautifulSoup


def is_valid(url):

    try:
        parsed = urlparse(url)
        host = parsed.hostname
    except ValueError:
        return False

    if parsed.scheme != "http" and parsed.scheme != "https":
        return False

    if host == None:
        return False

    allowed_domains = ["ics.uci.edu",
                       "cs.uci.edu",
                       "informatics.uci.edu",
                       "stat.uci.edu"]
    allowed = False

    for domain in allowed_domains:
        if host == domain or host.endswith("." + domain):
            allowed = True

    if allowed == False:
        return False

    path = parsed.path.lower()
    blocked = [ ".css", ".js", ".bmp", ".gif", ".jpg", ".jpeg", ".ico", ".png", ".tif", ".tiff", ".svg", ".webp", ".mid", ".mp2", ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mpeg", ".ram", ".m4v", ".mkv",
                ".ogg", ".ogv",".pdf", ".ps", ".eps", ".tex", ".ppt", ".pptx", ".doc", ".docx", ".xls", ".xlsx", ".names", ".data", ".dat", ".exe", ".bz2", ".tar", ".msi", ".bin", ".7z", ".psd", ".dmg",
                ".iso", ".epub", ".dll", ".cnf", ".tgz", ".sha1", ".thmx", ".mso", ".arff", ".rtf", ".jar", ".csv", ".rm", ".smil", ".wmv", ".swf", ".wma", ".zip", ".rar", ".gz" ]

    for extension in blocked:
        if path.endswith(extension):
            return False

    return True

def get_links(page_url, html):
    links = []
    page = BeautifulSoup(html, "html.parser")
    base_url = page_url
    base_tag = page.find("base", href = True)
    if base_tag != None:
        base_href = base_tag.get("href")
        try:
            base_url = urljoin(page_url, base_href)
        except ValueError:
            base_url = page_url

    tags = page.find_all("a")

    for tag in tags:
        href = tag.get("href")
        if href != None:
            href = href.strip()

            if href != "":
                clean_url = None

                try:
                    full_url = urljoin(base_url, href)

                    clean_url = full_url
                    if "#" in clean_url:
                        position = clean_url.find("#")
                        clean_url = clean_url[:position]

                    clean_url = quote(clean_url, safe = ":/?&=#%+;,@!$'()*[]-._~")

                except ValueError:
                    clean_url = None

                if clean_url != None:
                    if is_valid(clean_url):
                        if clean_url not in links:
                            links.append(clean_url)

    return links