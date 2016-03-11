from datetime import datetime, timedelta
import logging
import re
from time import sleep
import traceback

import validators
from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class KatProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = Session()

        # URLs
        self.url = 'https://kat.cr'
        self.urls = {
            'base': self.url,
            'search': urljoin(self.url, '%s/')
        }
        self.custom_url = None

        # Credentials
        self.public = True

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None
        self.confirmed = True

        # Search Params
        self.search_params = {
            'q': '',
            'field': 'seeders',
            'sorder': 'desc',
            'rss': 1,
            'category': ('tv', 'anime')
        }

        # Categories

        # Proper Strings

        # Options
