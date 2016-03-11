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
    with BS4Parser(data, 'html5lib') as soup:
        torrent_table = soup.find('table', class_='listing')
        torrent_rows = torrent_table('tr') if torrent_table else []

        # Continue only if at least one Release is found
        if len(torrent_rows) < 2:
            log.debug('Data returned from provider does not contain any torrents')
            return  items

        a = 1 if len(torrent_rows[0]('td')) < 2 else 0

        for top, bot in zip(torrent_rows[a::2], torrent_rows[a + 1::2]):
            desc_top = top.find('td', class_='desc-top')
            title = desc_top.get_text(strip=True)
            download_url = desc_top.find('a')['href']

            desc_bottom = bot.find('td', class_='desc-bot').get_text(strip=True)
            torrent_size = desc_bottom.split('|')[1].strip('Size: ')

            stats = bot.find('td', class_='stats').get_text(strip=True)
            sl = re.match(r'S:(?P<seeders>\d+)L:(?P<leechers>\d+)C:(?:\d+)ID:(?:\d+)', stats.replace(' ', ''))
            seeders = sl.group('seeders') if sl else 0
            leechers = sl.group('leechers') if sl else 0

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
