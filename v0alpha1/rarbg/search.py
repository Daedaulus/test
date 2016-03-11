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
        if ep_obj is not None:
            ep_indexerid = ep_obj.show.indexerid
            ep_indexer = ep_obj.show.indexer
        else:
            ep_indexerid = None
            ep_indexer = None
        if mode == 'RSS':
            search_params['sort'] = 'last'
            search_params['mode'] = 'list'
            search_params.pop('search_string', None)
            search_params.pop('search_tvdb', None)
        else:
            search_params['sort'] = provider.sorting if provider.sorting else 'seeders'
            search_params['mode'] = 'search'
            if ep_indexer == INDEXER_TVDB and ep_indexerid:
                search_params['search_tvdb'] = ep_indexerid
            else:
                search_params.pop('search_tvdb', None)
        for search_string in search_strings[mode]:
            if mode != 'RSS':
                search_params['search_string'] = search_string
            if mode != 'RSS':
                log.debug('Search string: {search}'.format(search=search_string))
            data = provider.session.get(search_url, params=search_params)
            if not data.content:
                log.debug('Data returned from provider does not contain any torrents')
            searches.append(data)
    return searches
