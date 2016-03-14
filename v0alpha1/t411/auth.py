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


# Log in
def login(self, login_params):
    if self.token is not None:
        if time.time() < (self.tokenLastUpdate + 30 * 60):
            return True

    response = self.get_url(self.urls['login_page'], post_data=login_params, returns='json')
    if not response:
        logger.log(u"Unable to connect to provider", logger.WARNING)
        return False

    if response and 'token' in response:
        self.token = response['token']
        self.tokenLastUpdate = time.time()
        # self.uid = response['uid'].encode('ascii', 'ignore')
        self.session.auth = T411Auth(self.token)
        return True
    else:
        logger.log(u"Token not found in authentication response", logger.WARNING)
        return False

# Validate login
def check_auth(self):
    raise NotImplementedError


class T411Auth(AuthBase):  # pylint: disable=too-few-public-methods
"""Attaches HTTP Authentication to the given Request object."""
def __init__(self, token):
    self.token = token

def __call__(self, r):
    r.headers['Authorization'] = self.token
    return r
