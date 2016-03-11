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
    searches = []
    for mode in search_strings:  # Mode = RSS, Season, Episode
        log.debug('Search Mode: {}'.format(mode))

        for search_string in search_strings[mode]:
            search_url = self.urls['search'] if mode != 'RSS' else self.urls['rss']
            if self.custom_url:
                if not validators.url(self.custom_url):
                    log.warn('Invalid custom url: {}'.format(self.custom_url))
                    return None
                search_url = urljoin(self.custom_url, search_url.split(self.url)[1])

            if mode != 'RSS':
                search_params['q'] = search_string
                log.debug('Search string: {search}'.format(search=search_string.decode('utf-8')))

                data = self.session.get(search_url, params=search_params)
            else:
                data = self.session.get(search_url)
            if not data.content:
                log.debug('Data returned from provider does not contain any torrents')
            searches.append(data)
    return searches
