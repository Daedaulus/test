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
        torrent_table = html.find('table', border='1')
        torrent_rows = torrent_table('tr') if torrent_table else []

        # Continue only if at least one Release is found
        if len(torrent_rows) < 2:
            log.debug('Data returned from provider does not contain any torrents')
            return items

        labels = [label.get_text(strip=True) for label in torrent_rows[0]('td')]

        # Skip column headers
        for result in torrent_rows[1:]:
            cells = result('td')

            download_url = urljoin(self.url, cells[labels.index('Name')].find('a', href=re.compile(r'download.php\?id='))['href'])
            title_element = cells[labels.index('Name')].find('a', href=re.compile(r'details.php\?id='))
            title = title_element.get('title', '') or title_element.get_text(strip=True)
            if not all([title, download_url]):
                continue

            if self.freeleech:
                # Free leech torrents are marked with green [F L] in the title (i.e. <font color=green>[F&nbsp;L]</font>)
                freeleech = cells[labels.index('Name')].find('font', color='green')
                if not freeleech or freeleech.get_text(strip=True) != '[F\xa0L]':
                    continue

            seeders = cells[labels.index('Seeders')].get_text(strip=True)
            leechers = cells[labels.index('Leechers')].get_text(strip=True)

            # Filter unseeded torrent
            if seeders < self.min_seed or leechers < self.min_leech:
                if mode != 'RSS':
                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                continue

            torrent_size = cells[labels.index('Size')].get_text(strip=True)

            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}

            if mode != 'RSS':
                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

            items.append(item)
        return items
