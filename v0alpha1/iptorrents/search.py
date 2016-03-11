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


# Search page
def search(
    self,
    search_strings,
    search_params,
    torrent_method=None,
    ep_obj=None,
    *args, **kwargs
):
    if not self.login():
        return None

    freeleech = '&free=on' if self.freeleech else ''

    for mode in search_strings:  # Mode = RSS, Season, Episode
        log.debug('Search Mode: {}'.format(mode))

        for search_string in search_strings[mode]:
            if mode != 'RSS':
                log.debug('Search string: {search}'.format(search=search_string.decode('utf-8')))

            search_url = self.urls['search'] % (self.categories, freeleech, search_string)
            search_url += ';o=seeders' if mode != 'RSS' else ''
            data = self.session.get(search_url).text
            if not data:
                log.debug('Data returned from provider does not contain any torrents')
