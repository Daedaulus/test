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


# Log in
def login(self, login_params):
    if any(dict_from_cookiejar(self.session.cookies).values()):
        return True

    response = self.session.post(self.urls['login'], data=login_params).text
    if not response:
        log.warn('Unable to connect to provider')
        return False

    # Invalid username and password combination
    if re.search('Invalid Username/password', response) or re.search('<title>Login :: TorrentLeech.org</title>', response):
        log.warn('Invalid username or password. Check your settings')
        return False

    return True


# Validate login
def check_auth(self):
    raise NotImplementedError
