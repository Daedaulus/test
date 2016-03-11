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
    if not data.startswith('<?xml'):
        log.info('Expected xml but got something else, is your mirror failing?')
        return items

    with BS4Parser(data, 'html5lib') as parser:
        for item in parser.findAll('item'):
            if item.category and 'tv' not in item.category.get_text(strip=True):
                continue

            title = item.title.text.rsplit(' ', 1)[0].replace(' ', '.')
            t_hash = item.guid.text.rsplit('/', 1)[-1]

            if not all([title, t_hash]):
                continue

            download_url = 'magnet:?xt=urn:btih:' + t_hash + '&dn=' + title + self._custom_trackers
            torrent_size, seeders, leechers = self._split_description(item.find('description').text)

            # Filter unseeded torrent
            if seeders < self.min_seed or leechers < self.min_leech:
                if mode != 'RSS':
                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                continue

            result = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': t_hash}
            items.append(result)

    return items
