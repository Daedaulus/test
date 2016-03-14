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
    # TODO: Enable Custom URL Support

    searches = []
    # TEMPORARY HACK! Force anime
    anime = kwargs.pop('is_anime', True)
    if not anime:
        return searches

    # Authenticate
    with suppress(NotImplementedError, AttributeError):
        if not provider.login(provider.login_params):
            return searches

    for mode in search_strings:  # Mode = RSS, Season, Episode
        log.debug('Search Mode: {}'.format(mode))
        for search_string in search_strings[mode]:
            # Select URL
            search_url = provider.urls.get(mode.lower(), search_url)

            # Update params
            if mode != 'RSS':
                search_params['term'] = search_string

            # Log search string
            if mode != 'RSS':
                log.debug('Search string: {search}'.format(search=search_string))
            # data = provider.cache.getRSSFeed(provider.url, params=search_params)['entries']

            # Execute Search
            data = provider.session.get(search_url, params=search_params)

            # Confirm content
            if not data.content:
                log.debug('Data returned from provider does not contain any torrents')
                continue

            # Append search result
            searches.append(data)
    return searches
