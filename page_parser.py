"""Part B: response checking and text extraction. This module never downloads pages."""





import logging
import re
from urllib.parse import urljoin, urldefrag, urlparse
 
from bs4 import BeautifulSoup, UnicodeDammit
 
from trap_detector import is_dead_page

# -----------------------------------------------------statuses---------------------

