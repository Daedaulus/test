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


# Search page
def search(
    self,
    search_strings,
    search_params,
    torrent_method=None,
    ep_obj=None,
    *args, **kwargs
):
    results = []

    if not self.login():
        return results

    for mode in search_strings:  # Mode = RSS, Season, Episode
        items = []
        log.debug('Search Mode: {}'.format(mode))

        for search_string in search_strings[mode]:

            if mode != 'RSS':
                log.debug('Search string: {}'.format(search_string.decode('utf-8')))

            search_params['search'] = search_string
            data = self.session.get(self.urls['search'], params=search_params).text
            if not data:
                log.debug('No data returned from provider')
                continue
