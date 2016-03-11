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
    searches = []
    with suppress(NotImplementedError, AttributeError):
        if not provider.login(provider.login_params):
            return searches
    for mode in search_strings:  # Mode = RSS, Season, Episode
        log.debug('Search Mode: {}'.format(mode))
        for search_string in search_strings[mode]:
            categories = ['2', '7', '35', ]
            categories += (
                ['26', '27', '32', '34', ] if mode == 'RSS' else
                ['26', '32'] if mode == 'Episode' else
                ['27']
            )
            if provider.show and provider.show.is_anime:
                categories += ['34']
            search_params = {
                'categories': ','.join(categories),
                'query': search_string
            }
            if mode != 'RSS':
                log.debug('Search string: {search}'.format(search=search_string))
            data = provider.session.get(search_url, params=search_params)
            if not data.content:
                log.debug('Data returned from provider does not contain any torrents')
            searches.append(data)
    return searches
