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
        self.url = 'https://torrentleech.org'
        self.urls = {
            'base': self.url,
            'login': urljoin(self.url, 'user/account/login/'),
            'search': urljoin(self.url, 'torrents/browse'),
        }

        # Credentials
        self.username = kwargs.pop('username', None)
        self.password = kwargs.pop('password', None)
        self.login_params = {
            'username': self.username.encode('utf-8'),
            'password': self.password.encode('utf-8'),
            'login': 'submit',
            'remember_me': 'on',
        }

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None

        # Search Params

        # Categories

        # Proper Strings
        self.proper_strings = [
            'PROPER',
            'REPACK',
        ]

        # Options
