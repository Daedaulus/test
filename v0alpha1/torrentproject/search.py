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
    for mode in search_strings:  # Mode = RSS, Season, Episode
        log.debug('Search Mode: {}'.format(mode))

        for search_string in search_strings[mode]:
            if mode != 'RSS':
                log.debug('Search string: {search}'.format(search=search_string.decode('utf-8')))

            search_params['s'] = search_string

            if self.custom_url:
                if not validators.url(self.custom_url):
                    log.warn('Invalid custom url set, please check your settings')
                    return None
                search_url = self.custom_url
            else:
                search_url = self.url

            torrents = self.session.get(search_url, params=search_params).json()
            if not (torrents and 'total_found' in torrents and int(torrents['total_found']) > 0):
                log.debug('Data returned from provider does not contain any torrents')
