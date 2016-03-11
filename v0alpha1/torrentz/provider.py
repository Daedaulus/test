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


class TorrentzProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'https://torrentz.eu/'
        self.urls = {
            'base': self.url,
            'verified': urljoin(self.url, 'feed_verified'),
            'feed': urljoin(self.url, 'feed'),
        }

        # Credentials
        self.public = True

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None
        self.confirmed = True

        # Search Params

        # Categories

        # Proper Strings

        # Options
