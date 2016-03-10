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
log.addHandler(logging.NullHandler)


class RarbgProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'https://rarbg.com'  # Spec: https://torrentapi.org/apidocs_v2.txt
        self.urls = {
            'base': self.url,
            'api': 'http://torrentapi.org/pubapi_v2.php'
        }

        # Credentials
        self.public = True
        self.token = None
        self.token_expires = None
        self.login_params = {
            'get_token': 'get_token',
            'format': 'json',
            'app_id': 'medusa'
        }

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None

        # Search Params
        self.ranked = None
        self.sorting = None
        self.search_params = {
            'app_id': 'sickrage2',
            'category': 'tv',
            'min_seeders': self.min_seed,
            'min_leechers': self.min_leech,
            'limit': 100,
            'format': 'json_extended',
            'ranked': self.ranked,
            'token': self.token,
        }

        # Categories

        # Proper Strings
        self.proper_strings = [
            '{{PROPER|REPACK}}',
        ]

        # Options
