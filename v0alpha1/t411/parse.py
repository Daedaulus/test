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

    if 'torrents' not in data and mode != 'RSS':
        log.debug(u"Data returned from provider does not contain any torrents")
        return items

    torrents = data['torrents'] if mode != 'RSS' else data

    if not torrents:
        log.debug(u"Data returned from provider does not contain any torrents")
        return items

    for torrent in torrents:
        if mode == 'RSS' and 'category' in torrent and torrent['category'] not in self.subcategories:
            continue

        title = torrent['name']
        torrent_id = torrent['id']
        download_url = (self.urls['download'] % torrent_id).encode('utf8')
        if not all([title, download_url]):
            continue

        seeders = torrent['seeders']
        leechers = torrent['leechers']
        verified = bool(torrent['isVerified'])
        torrent_size = torrent['size']

        # Filter unseeded torrent
        if seeders < self.minseed or leechers < self.minleech:
            if mode != 'RSS':
                log.debug(u"Discarding torrent because it doesn't meet the minimum seeders or leechers: {} (S:{} L:{})".format(title, seeders, leechers))
            continue

        if self.confirmed and not verified and mode != 'RSS':
            log.debug(u"Found result " + title + " but that doesn't seem like a verified result so I'm ignoring it")
            continue

        item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
        if mode != 'RSS':
            log.debug(u"Found result: %s with %s seeders and %s leechers" % (title, seeders, leechers))

        items.append(item)
    return items
