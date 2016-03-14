from datetime import datetime, timedelta
import logging
import re
from time import sleep
import traceback

import validators
from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar
from requests_toolbelt.utils.user_agent import user_agent

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

        # URLs
        self.url = 'https://btdigg.org/'
        self.urls = {
            'api': 'https://api.btdigg.org/api/private-341ada3245790954/s02/',
            'rss': 'https://api.btdigg.org/api/private-341ada3245790954/s02/',
            'search': 'https://api.btdigg.org/api/private-341ada3245790954/s02/',
        }

        # Credentials
        self.public = True

        # Torrent Stats

        # Search Params
        self.search_params = {
            'p': 0
        }

        # Categories

        # Proper Strings
        self.proper_strings = [
            'PROPER',
            'REPACK',
        ]

        # Options
