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


class ABNormalProvider:

    def __init__(self):

        self.session = Session()

        # Credentials
        self.username = None
        self.password = None
        self.login_params = {
            'username': self.username,
            'password': self.password,
        }

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None

        # URLs
        self.url = 'https://abnormal.ws'
        self.urls = {
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'torrents.php'),
        }

        # Proper Strings
        self.proper_strings = [
            'PROPER',
        ]

        # Search Params
        self.search_params = {
            'cat[]': [
                'TV|SD|VOSTFR',
                'TV|HD|VOSTFR',
                'TV|SD|VF',
                'TV|HD|VF',
                'TV|PACK|FR',
                'TV|PACK|VOSTFR',
                'TV|EMISSIONS',
                'ANIME',
            ],
            'way': 'DESC'  # Both ASC and DESC are available for sort direction
        }

    def search(self, search_strings, search_params):
        results = []

        if not self.login():
            return results

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}'.format(search=search_string.decode('utf-8')))

                search_params['order'] = ('Seeders', 'Time')[mode == 'RSS']
                search_params['search'] = re.sub(r'[()]', '', search_string)
                data = self.session.get(self.urls['search'], params=search_params).text
                if not data:
                    log.debug('No data returned from provider')
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find(class_='torrent_table')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    labels = [label.get_text(strip=True) for label in torrent_rows[0]('td')]

                    # Skip column headers
                    for result in torrent_rows[1:]:
                        cells = result('td')
                        if len(cells) < len(labels):
                            continue

                        try:
                            title = cells[labels.index('Release')].get_text(strip=True)
                            download_url = urljoin(self.url, cells[labels.index('DL')].find('a', class_='tooltip')['href'])
                            if not all([title, download_url]):
                                continue

                            seeders = cells[labels.index('S')].get_text(strip=True)
                            leechers = cells[labels.index('L')].get_text(strip=True)

                            # Filter unseeded torrent
                            if seeders < self.min_seed or leechers < self.min_leech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            size_index = labels.index('Size') if 'Size' in labels else labels.index('Taille')
                            torrent_size = cells[size_index].get_text()

                            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}

                            if mode != 'RSS':
                                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                            items.append(item)

                        except Exception:
                            continue

            results += items

        return results

    def login(self, session, login_params):
        if any(dict_from_cookiejar(session.cookies).values()):
            return True

        response = session.post(self.urls['login'], data=login_params).text
        if not response:
            log.warn('Unable to connect to provider')
            return False

        # Invalid username and password combination
        if not re.search('torrents.php', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True
