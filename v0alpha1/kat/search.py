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

    # TEMPORARY HACK! Anime check needs moved outside of search, ignoring for now
    # anime = (provider.show and provider.show.anime) or (ep_obj and ep_obj.show and ep_obj.show.anime) or False
    anime = kwargs.pop('is_anime', False)
    searches = []
    # Authenticate
    with suppress(NotImplementedError, AttributeError):
        if not provider.login(provider.login_params):
            return searches

    for mode in search_strings:  # Mode = RSS, Season, Episode
        log.debug('Search Mode: {}'.format(mode))
        for search_string in search_strings[mode]:
            # Select URL
            search_url = provider.urls.get(mode.lower(), search_url)
            # TODO: Find out why this was done, disable for now
            # urljoin(provider.urls['rss'], search_string)

            # Update params
            search_params['category'] = search_params['category'][anime]
            search_params['q'] = '' if mode == 'RSS' else search_string
            search_params['field'] = 'time_add' if mode == 'RSS' else 'seeders'

            # Log search string
            if mode != 'RSS':
                log.debug('Search string: {search}'.format(search=search_string))

            # Execute Search
            data = provider.session.get(search_url, params=search_params)

            # Confirm content
            if not data.content:
                log.debug('Data returned from provider does not contain any torrents')
                continue

            # Append search result
            searches.append(data)
    return searches
