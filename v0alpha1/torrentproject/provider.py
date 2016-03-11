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
        self.url = 'https://torrentproject.se/'
        self.urls = {
            'base': self.url,
        }
        self.custom_url = None

        # Credentials
        self.public = True

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None
        self.min_seed = None
        self.min_leech = None

        # Search Params
        self.search_params = {
            'out': 'json',
            'filter': 2101,
            'num': 150
        }

        # Categories

        # Proper Strings

        # Options
