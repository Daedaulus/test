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
    if any(dict_from_cookiejar(self.session.cookies).values()):
        return True
    log.debug(self.name)
    log.debug(self.session.cookies)
    response = self.session.get(self.urls['login'], data=login_params)
    log.debug(response.cookies)
    log.debug(self.session.cookies)
    response = self.session.post(self.urls['login'], data=login_params)
    log.debug(response.cookies)
    log.debug(response.request.headers)
    log.debug(self.session.cookies)
    if not response.text:
        log.warn('Unable to connect to provider')
        return False

    # Invalid username and password combination
    if re.search('Your username or password was incorrect.', response.text):
        log.warn('Invalid username or password. Check your settings')
        return False

    return True


# Validate login
def check_auth(self):
    if not self.username or not self.password:
        raise Exception('Your authentication credentials for ' + self.name + ' are missing, check your config.')

    return True
