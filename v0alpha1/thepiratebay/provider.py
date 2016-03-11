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


class Provider:
    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'https://thepiratebay.se/'
        self.urls = {
            'base': self.url,
            'rss': urljoin(self.url, 'browse/200'),
            'search': urljoin(self.url, 's/'),  # Needs trailing /
        }
        self.custom_url = None

        # Credentials
        self.public = True

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None
        self.confirmed = True

        # Proper Strings

        # Search Params
        self.search_params = {
            'q': '',
            'type': 'search',
            'orderby': 7,
            'page': 0,
            'category': 200
        }

        # Categories

        # Proper Strings

        # Options
