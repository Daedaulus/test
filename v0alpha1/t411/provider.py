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
        self.headers.update({'User-Agent': USER_AGENT})

        # URLs
        self.urls = {'base_url': 'http://www.t411.ch/',
                     'search': 'https://api.t411.ch/torrents/search/%s*?cid=%s&limit=100',
                     'rss': 'https://api.t411.ch/torrents/top/today',
                     'login_page': 'https://api.t411.ch/auth',
                     'download': 'https://api.t411.ch/torrents/download/%s'}
        self.url = self.urls['base_url']

        # Credentials
        self.username = None
        self.password = None
        self.token = None
        self.tokenLastUpdate = None
        self.login_params = {
            'username': self.username,
            'password': self.password
        }

        # Torrent Stats
        self.minseed = 0
        self.minleech = 0
        self.confirmed = False

        # Search Params

        # Categories
        self.subcategories = [433, 637, 455, 639]

        # Proper Strings

        # Options
