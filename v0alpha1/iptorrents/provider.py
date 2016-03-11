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
        self.url = 'https://iptorrents.eu/'
        self.urls = {
            'base': self.url,
            'login': urljoin(self.url, 'torrents/'),
            'search': urljoin(self.url, 't?%s%s&q=%s&qf=#torrents'),
        }

        # Credentials
        self.username = kwargs.pop('username', None)
        self.password = kwargs.pop('password', None)
        self.login_params = {
            'username': self.username,
            'password': self.password,
            'login': 'submit',
        }

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None
        self.freeleech = False

        # Proper Strings

        # Search Params

        # Categories
        self.categories = '73=&60='

        # Proper Strings

        # Options
