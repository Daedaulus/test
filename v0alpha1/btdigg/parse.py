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


# Parse page for results
def parse(self, data, mode, torrent_method):
    items = []
    for torrent in data:
        title = torrent.pop('name', '')
        download_url = torrent.pop('magnet') + self._custom_trackers if torrent['magnet'] else None
        if not all([title, download_url]):
            continue

        if float(torrent.pop('ff')):
            log.debug('Ignoring result for {} since it\'s been reported as fake (level = {})'.format(title, torrent['ff']))
            continue

        if not int(torrent.pop('files')):
            log.debug('Ignoring result for {} because it has no files'.format(title))
            continue

        # Provider doesn't provide seeders/leechers
        seeders = 1
        leechers = 0

        torrent_size = torrent.pop('size')

        item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
        if mode != 'RSS':
            log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

            items.append(item)

    return items
