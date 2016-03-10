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
def parse(self, data, mode):
    items = []
    data = re.sub(r'(?im)<button.+?<[/]button>', '', data, 0)
    with BS4Parser(data, 'html5lib') as html:
        if not html:
            log.debug('No data returned from provider')
            return items

        if html.find(text='No Torrents Found!'):
            log.debug('Data returned from provider does not contain any torrents')
            return items

        torrent_table = html.find('table', attrs={'class': 'torrents'})
        torrents = torrent_table('tr') if torrent_table else []

        # Continue only if one Release is found
        if len(torrents) < 2:
            log.debug('Data returned from provider does not contain any torrents')
            return items

        # Skip column headers
        for result in torrents[1:]:
            title = result('td')[1].find('a').text
            download_url = self.urls['base'] + result('td')[3].find('a')['href']
            if not all([title, download_url]):
                continue

            seeders = int(result.find('td', attrs={'class': 'ac t_seeders'}).text)
            leechers = int(result.find('td', attrs={'class': 'ac t_leechers'}).text)

            # Filter unseeded torrent
            if seeders < self.min_seed or leechers < self.min_leech:
                if mode != 'RSS':
                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                continue

            torrent_size = result('td')[5].text

            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}

            if mode != 'RSS':
                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

            items.append(item)

    return items
