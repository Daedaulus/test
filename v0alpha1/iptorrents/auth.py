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

    self.session.get(self.urls['login'])
    response = self.session.post(self.urls['login'], data=login_params).text
    if not response:
        log.warn('Unable to connect to provider')
        return False

    # Invalid username and password combination
    if re.search('Invalid username and password combination', response):
        log.warn('Invalid username or password. Check your settings')
        return False

    # You tried too often, please try again after 2 hours!
    if re.search('You tried too often', response.text):
        log.warn('You tried too often, please try again after 2 hours! Disable IPTorrents for at least 2 hours')
        return False

    return True


# Validate login
def check_auth(self):
    if not self.username or not self.password:
        raise Exception('Your authentication credentials for ' + self.name + ' are missing, check your config.')
    return True
