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
        self.url = 'https://abnormal.ws/'
        self.urls = {
            'base': self.url,
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'torrents.php'),
        }

        # Credentials
        self.username = kwargs.pop('username', None)
        self.password = kwargs.pop('password', None)
        self.login_params = {
            'username': self.username,
            'password': self.password,
        }

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None

        # Search Params
        self.search_params = {
            'cat[]': [
                'TV|SD|VOSTFR',
                'TV|HD|VOSTFR',
                'TV|SD|VF',
                'TV|HD|VF',
                'TV|PACK|FR',
                'TV|PACK|VOSTFR',
                'TV|EMISSIONS',
                'ANIME',
            ],
            'way': 'DESC'  # Both ASC and DESC are available for sort direction
        }

        # Categories

        # Proper Strings
        self.proper_strings = [
            'PROPER',
        ]

        # Options
