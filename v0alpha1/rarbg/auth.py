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
    if self.token and self.token_expires and datetime.now() < self.token_expires:
        return True

    response = self.session.get(self.urls['api'], params=login_params).json()
    if not response:
        log.warn('Unable to connect to provider')
        return False

    self.token = response.get('token', None)
    self.token_expires = datetime.now() + timedelta(minutes=14) if self.token else None

    return self.token is not None


# Validate login
def check_auth(self):
    raise NotImplementedError
