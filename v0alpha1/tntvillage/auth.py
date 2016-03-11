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
    if len(self.session.cookies) >= 3:
        if self.session.cookies.get('pass_hash', '') not in ('0', 0) and self.session.cookies.get('member_id') not in ('0', 0):
            return True

    response = self.session.post(self.urls['login'], data=login_params).text
    if not response:
        log.warn('Unable to connect to provider')
        return False

    # Invalid username and password combination
    if re.search('Sono stati riscontrati i seguenti errori', response) or re.search('<title>Connettiti</title>', response):
        log.warn('Invalid username or password. Check your settings')
        return False

    return True


# Validate login
def check_auth(self):
    if not self.username or not self.password:
        raise Exception('Your authentication credentials for ' + self.name + ' are missing, check your config.')
    return True

