from datetime import datetime, timedelta
import logging
import re
from time import sleep
import traceback

import validators
from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar
from requests.utils import cookiejar_from_dict

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Provider:
    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())
        self.session.headers['User-Agent'] = 'Medusa'
        self.session.headers['Accept-Encoding'] = 'gzip,deflate'
        self.session.cookies = cookiejar_from_dict({})

        # URLs
        self.url = 'https://www.morethan.tv/'
        self.urls = {
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'torrents.php'),
        }

        # Credentials
        self.username = None
        self.password = None
        self._uid = None
        self._hash = None
        self.login_params = {
            'username': self.username,
            'password': self.password,
            'keeplogged': '1',
            'login': 'Log in',
        }

        # Torrent Stats
        self.minseed = None
        self.minleech = None
        self.freeleech = None

        # Search Params
        self.search_params = {
            'tags_type': 1,
            'order_by': 'time',
            'order_way': 'desc',
            'action': 'basic',
            'searchsubmit': 1,
            'searchstr': ''
        }

        # Categories

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Options
