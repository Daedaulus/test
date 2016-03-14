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
        self.url = 'http://www.newpct.com'
        self.urls = {
            'base': self.url,
            'search': urljoin(self.url, 'index.php')
        }

        # Credentials

        # Torrent Stats

        # Search Params
        self.search_params = {
            'l': 'doSearch',
            'q': '',
            'category_': 'All',
            'idioma_': 1,
            'bus_de_': 'All'
        }

        # Categories

        # Proper Strings

        # Options
        self.onlyspasearch = None
