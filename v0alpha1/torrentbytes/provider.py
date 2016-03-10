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


class TorrentBytesProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'https://www.torrentbytes.net/'
        self.urls = {
            'base': self.url,
            'login': urljoin(self.url, 'takelogin.php'),
            'search': urljoin(self.url, 'browse.php')
        }

        # Credentials
        self.username = None
        self.password = None
        self.login_params = {
            'username': self.username,
            'password': self.password,
            'login': 'Log in!'
        }

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None
        self.freeleech = False

        # Search Params
        self.search_params = {
            'c41': 1,
            'c33': 1,
            'c38': 1,
            'c32': 1,
            'c37': 1
        }

        # Categories

        # Proper Strings
        self.proper_strings = [
            'PROPER',
            'REPACK',
        ]

        # Options
