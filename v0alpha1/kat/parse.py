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
    with BS4Parser(data, 'html5lib') as document:
        if not document._is_xml:
            log.info('Expected xml but got something else, is your mirror failing?')
            return items

        for item in document('item'):
            title = item.title.get_text(strip=True)
            # Use the torcache link kat provides,
            # unless it is not torcache or we are not using blackhole
            # because we want to use magnets if connecting direct to client
            # so that proxies work.
            download_url = item.enclosure['url']
            if torrent_method != 'blackhole' or 'torcache' not in download_url:
                download_url = item.find('torrent:magneturi').next.replace('CDATA', '').strip('[!]') + self._custom_trackers

            if not (title and download_url):
                continue

            seeders = item.find('torrent:seeds').get_text(strip=True)
            leechers = item.find('torrent:peers').get_text(strip=True)

            # Filter unseeded torrent
            if seeders < self.min_seed or leechers < self.min_leech:
                if mode != 'RSS':
                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                continue

            verified = bool(int(item.find('torrent:verified').get_text(strip=True)))
            if self.confirmed and not verified:
                if mode != 'RSS':
                    log.debug('Found result ' + title + ' but that doesn\'t seem like a verified result so I\'m ignoring it')
                continue

            torrent_size = item.find('torrent:contentlength').get_text(strip=True)
            info_hash = item.find('torrent:infohash').get_text(strip=True)

            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': info_hash}
            if mode != 'RSS':
                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

            items.append(item)

    return items
