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
            title = re.sub(r'^<!\[CDATA\[|\]\]>$', '', item.find('title').get_text(strip=True))
            seeders = item.find('seeders').get_text(strip=True)
            leechers = item.find('leechers').get_text(strip=True)
            torrent_size = item.find('size').get_text()

            if torrent_method == 'blackhole':
                enclosure = item.find('enclosure')  # Backlog doesnt have enclosure
                download_url = enclosure['url'] if enclosure else item.find('link').next.strip()
                download_url = re.sub(r'(.*)/torrent/(.*).html', r'\1/download/\2.torrent', download_url)
            else:
                info_hash = item.find('info_hash').get_text(strip=True)
                download_url = 'magnet:?xt=urn:btih:' + info_hash + '&dn=' + title + self._custom_trackers

            if not all([title, download_url]):
                continue

            # Filter unseeded torrent
            if seeders < self.min_seed or leechers < self.min_leech:
                if mode != 'RSS':
                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                continue

            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
            if mode != 'RSS':
                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

            items.append(item)

    return items
