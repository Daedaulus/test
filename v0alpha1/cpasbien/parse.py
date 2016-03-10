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
        torrent_rows = html(class_=re.compile('ligne[01]'))
        for result in torrent_rows:
            title = result.find(class_='titre').get_text(strip=True).replace('HDTV', 'HDTV x264-CPasBien')
            title = re.sub(r' Saison', ' Season', title, flags=re.IGNORECASE)
            tmp = result.find('a')['href'].split('/')[-1].replace('.html', '.torrent').strip()
            download_url = (self.url + '/telechargement/%s' % tmp)
            if not all([title, download_url]):
                continue

            seeders = result.find(class_='up').get_text(strip=True)
            leechers = result.find(class_='down').get_text(strip=True)

            # Filter unseeded torrent
            if seeders < self.min_seed or leechers < self.min_leech:
                if mode != 'RSS':
                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                continue

            torrent_size = result.find(class_='poid').get_text(strip=True)

            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}

            if mode != 'RSS':
                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

            items.append(item)
    return items
