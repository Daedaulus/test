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


# Parse page for results
def parse(self, data, mode, torrent_method):
    items = []
    for curItem in data:
        title = curItem['title']
        download_url = curItem['link']
        if not all([title, download_url]):
            continue

        item_info = self.regex.search(curItem['summary'])
        if not item_info:
            log.debug('There was a problem parsing an item summary, skipping: {}'.format(title))
            continue

        seeders, leechers, torrent_size, verified = item_info.groups()

        if seeders < self.min_seed or leechers < self.min_leech:
            if mode != 'RSS':
                log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
            continue

        if self.confirmed and not verified and mode != 'RSS':
            log.debug('Found result {} but that doesn\'t seem like a verified result so I\'m ignoring it'.format(title))
            continue

        result = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers}

        if mode != 'RSS':
            log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

        items.append(result)

    return items
