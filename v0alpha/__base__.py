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


class Provider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = kwargs.pop('url', None)
        self.urls = {
            'base': self.url,
        }

        # Credentials

        # Torrent Stats

        # Search Params

        # Categories

        # Proper Strings

        # Options

    # Search page
    def search(
        self,
        search_strings,
        search_params,
        torrent_method=None,
        ep_obj=None,
        *args, **kwargs
    ):
        raise NotImplementedError

    # Parse page for results
    def parse(self):
        raise NotImplementedError

    # Log in
    def login(self, login_params):
        raise NotImplementedError

    # Validate login
    def check_auth(self):
        raise NotImplementedError
