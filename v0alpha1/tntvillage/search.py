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
            provider.categories = 'cat=' + str(provider.cat)
            if mode == 'RSS':
                provider.page = 2
            last_page = 0
            pages = int(provider.page)
            if search_string == '':
                continue
            search_string = str(search_string).replace('.', ' ')
            for page in range(0, pages):
                offset = page * 20
                if last_page:
                    break
                search_url = (
                    provider.urls['search_page'].format(offset, provider.categories) if mode == 'RSS' else
                    (provider.urls['search_page'] + '&filter={2}').format(offset, provider.categories, search_string)
                )
                if mode != 'RSS':
                    log.debug('Search string: {search}'.format(search=search_string))
                data = provider.session.get(search_url, params=search_params)
                if not data.content:
                    log.debug('Data returned from provider does not contain any torrents')
                searches.append(data)
    return searches
