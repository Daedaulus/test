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
    with BS4Parser(data, 'html5lib') as html:
        torrent_table = html.find('table', id='torrenttable')
        torrent_rows = torrent_table('tr') if torrent_table else []

        # Continue only if at least one Release is found
        if len(torrent_rows) < 2:
            log.debug('Data returned from provider does not contain any torrents')
            return items

        labels = [process_column_header(label) for label in torrent_rows[0]('th')]

        # Skip column headers
        for result in torrent_rows[1:]:
            title = result.find('td', class_='name').find('a').get_text(strip=True)
            download_url = urljoin(self.url, result.find('td', class_='quickdownload').find('a')['href'])
            if not all([title, download_url]):
                continue

            seeders = result.find('td', class_='seeders').get_text(strip=True)
            leechers = result.find('td', class_='leechers').get_text(strip=True)

            # Filter unseeded torrent
            if seeders < self.min_seed or leechers < self.min_leech:
                if mode != 'RSS':
                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                continue

            torrent_size = result('td')[labels.index('Size')].get_text()

            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
            if mode != 'RSS':
                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

            items.append(item)

    return items


def process_column_header(td):
    col_header = ''
    if td.a:
        col_header = td.a.get('title')
    if not col_header:
        col_header = td.get_text(strip=True)
    return col_header
