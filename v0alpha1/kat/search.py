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
    anime = (self.show and self.show.anime) or (ep_obj and ep_obj.show and ep_obj.show.anime) or False
    search_params['category'] = search_params['category'][anime]

    for mode in search_strings:  # Mode = RSS, Season, Episode
        log.debug('Search Mode: {}'.format(mode))

        for search_string in search_strings[mode]:

            search_params['q'] = search_string if mode != 'RSS' else ''
            search_params['field'] = 'seeders' if mode != 'RSS' else 'time_add'

            if mode != 'RSS':
                log.debug('Search string: {}'.format(search_string.decode('utf-8')))

            search_url = self.urls['search'] % ('usearch' if mode != 'RSS' else search_string)
            if self.custom_url:
                if not validators.url(self.custom_url):
                    log.warn('Invalid custom url: {}'.format(self.custom_url))
                    return None
                search_url = urljoin(self.custom_url, search_url.split(self.url)[1])

            data = self.session.get(search_url, params=search_params).text
            if not data:
                log.debug('No data returned from provider')
                continue
