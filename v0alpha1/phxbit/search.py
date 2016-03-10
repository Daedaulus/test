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
    if not self.login():
        return None

    for mode in search_strings:  # Mode = RSS, Season, Episode
        log.debug('Search Mode: {}'.format(mode))

        for search_string in search_strings[mode]:

            if mode != 'RSS':
                # Use exact=1 parameter if we're doing a backlog or manual search
                search_params['exact'] = 1
                log.debug('Search string: {}'.format(search_string.decode('utf-8')))

            search_params['q'] = search_string
            data = self.session.get(self.urls['search'], params=search_params).text
            if not data:
                log.debug('No data returned from provider')
                continue
