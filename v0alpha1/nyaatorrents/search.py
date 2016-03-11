from contextlib import suppress
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
    provider,
    search_url,
    search_strings,
    search_params,
    torrent_method=None,
    ep_obj=None,
    *args, **kwargs
):
    # TEMPORARY HACK! Force anime
    anime = kwargs.pop('is_anime', True)
    searches = []
    with suppress(NotImplementedError, AttributeError):
        if not provider.login(provider.login_params):
            return searches
    if not anime:
        return searches
    for mode in search_strings:  # Mode = RSS, Season, Episode
        log.debug('Search Mode: {}'.format(mode))
        for search_string in search_strings[mode]:
            if mode != 'RSS':
                search_params['term'] = search_string
            if mode != 'RSS':
                log.debug('Search string: {search}'.format(search=search_string))
            # data = provider.cache.getRSSFeed(provider.url, params=search_params)['entries']
            data = provider.session.get(provider.url, params=search_params)
            if not data.content:
                log.debug('Data returned from provider does not contain any torrents')
            searches.append(data)
    return searches
