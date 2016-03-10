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

    if ep_obj is not None:
        ep_indexerid = ep_obj.show.indexerid
        ep_indexer = ep_obj.show.indexer
    else:
        ep_indexerid = None
        ep_indexer = None

    for mode in search_strings:  # Mode = RSS, Season, Episode
        log.debug('Search Mode: {}'.format(mode))
        if mode == 'RSS':
            search_params['sort'] = 'last'
            search_params['mode'] = 'list'
            search_params.pop('search_string', None)
            search_params.pop('search_tvdb', None)
        else:
            search_params['sort'] = self.sorting if self.sorting else 'seeders'
            search_params['mode'] = 'search'

            if ep_indexer == INDEXER_TVDB and ep_indexerid:
                search_params['search_tvdb'] = ep_indexerid
            else:
                search_params.pop('search_tvdb', None)

        for search_string in search_strings[mode]:

            if mode != 'RSS':
                search_params['search_string'] = search_string
                log.debug('Search string: {search}'.format(search=search_string.decode('utf-8')))

            sleep(cpu_presets[sickbeard.CPU_PRESET])
            data = self.session.get(self.urls['api'], params=search_params).json()
            if not isinstance(data, dict):
                log.debug('Data returned from provider does not contain any torrents')
