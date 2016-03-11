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
    if not self.login():
        return None

    self.categories = 'cat=' + str(self.cat)

    for mode in search_strings:  # Mode = RSS, Season, Episode
        log.debug('Search Mode: {}'.format(mode))

        for search_string in search_strings[mode]:

            if mode == 'RSS':
                self.page = 2

            last_page = 0
            y = int(self.page)

            if search_string == '':
                continue

            search_string = str(search_string).replace('.', ' ')

            for x in range(0, y):
                z = x * 20
                if last_page:
                    break

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))
                    search_url = (self.urls['search_page'] + '&filter={2}').format(z, self.categories, search_string)
                else:
                    search_url = self.urls['search_page'].format(z, self.categories)

                data = self.session.get(search_url).text
                if not data:
                   log.debug('Data returned from provider does not contain any torrents')
