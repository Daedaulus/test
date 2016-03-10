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
    with BS4Parser(data, 'html5lib') as html:
        torrent_table = html.find('table', id='searchResult')
        torrent_rows = torrent_table('tr') if torrent_table else []

        # Continue only if at least one Release is found
        if len(torrent_rows) < 2:
            log.debug('Data returned from provider does not contain any torrents')
            return items

        labels = [process_column_header(label) for label in torrent_rows[0]('th')]

        # Skip column headers
        for result in torrent_rows[1:]:
            cells = result('td')

            title = result.find(class_='detName').get_text(strip=True)
            download_url = result.find(title='Download this torrent using magnet')['href'] + self._custom_trackers
            if 'magnet:?' not in download_url:
                log.debug('Invalid ThePirateBay proxy please try another one')
                continue
            if not all([title, download_url]):
                continue

            seeders = cells[labels.index('SE')].get_text(strip=True)
            leechers = cells[labels.index('LE')].get_text(strip=True)

            # Filter unseeded torrent
            if seeders < self.min_seed or leechers < self.min_leech:
                if mode != 'RSS':
                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                continue

            # Accept Torrent only from Good People for every Episode Search
            if self.confirmed and not result.find(alt=re.compile(r'VIP|Trusted')):
                if mode != 'RSS':
                    log.debug('Found result {} but that doesn\'t seem like a trusted result so I\'m ignoring it'.format(title))
                continue

            torrent_size = cells[labels.index('Name')].find(class_='detDesc').get_text(strip=True).split(', ')[1]
            torrent_size = re.sub(r'Size ([\d.]+).+([KMGT]iB)', r'\1 \2', torrent_size)

            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}

            if mode != 'RSS':
                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

            items.append(item)
    return items


def process_column_header(th):
    col_header = ''
    if th.a:
        col_header = th.a.get_text(strip=True)
    if not col_header:
        col_header = th.get_text(strip=True)
    return col_header
