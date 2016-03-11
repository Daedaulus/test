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


class NyaaProvider:
    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'http://www.nyaa.se/'
        self.urls = {
            'base': self.url,
        }

        # Credentials
        self.public = True
        self.supports_absolute_numbering = True
        self.anime_only = True

        # Torrent Stats
        self.min_seed = 0
        self.min_leech = 0
        self.confirmed = False

        # Search Params
        self.search_params = {
            'page': 'rss',
            'cats': '1_0',  # All anime
            'sort': 2,  # Sort Descending By Seeders
            'order': 1
        }

        # Categories

        # Proper Strings

        # Options

        # Miscellaneous
        self.regex = re.compile(r'(\d+) seeder\(s\), (\d+) leecher\(s\), \d+ download\(s\) - (\d+.?\d* [KMGT]iB)(.*)', re.DOTALL)
