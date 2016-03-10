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


class TorrentLeechProvider:

    def __init__(self):

        self.session = Session()

        # Credentials
        self.username = None
        self.password = None

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None

        # URLs
        self.url = 'https://torrentleech.org'
        self.urls = {
            'login': urljoin(self.url, 'user/account/login/'),
            'search': urljoin(self.url, 'torrents/browse'),
        }

        # Proper Strings
        self.proper_strings = [
            'PROPER',
            'REPACK',
        ]

        # Search Params

    def search(self, search_strings):
        results = []

        if not self.login():
            return results

        def process_column_header(td):
            col_header = ''
            if td.a:
                col_header = td.a.get('title')
            if not col_header:
                col_header = td.get_text(strip=True)
            return col_header

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                    categories = ['2', '7', '35']
                    categories += ['26', '32'] if mode == 'Episode' else ['27']
                    if self.show and self.show.is_anime:
                        categories += ['34']
                else:
                    categories = ['2', '26', '27', '32', '7', '34', '35']

                search_params = {
                    'categories': ','.join(categories),
                    'query': search_string
                }

                data = self.session.get(self.urls['search'], params=search_params).text
                if not data:
                    log.debug('No data returned from provider')
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('table', id='torrenttable')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    labels = [process_column_header(label) for label in torrent_rows[0]('th')]

                    # Skip column headers
                    for result in torrent_rows[1:]:
                        try:
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

                        except Exception:
                            continue

            results += items

        return results

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username.encode('utf-8'),
            'password': self.password.encode('utf-8'),
            'login': 'submit',
            'remember_me': 'on',
        }

        response = self.session.post(self.urls['login'], data=login_params).text
        if not response:
            log.warn('Unable to connect to provider')
            return False

        # Invalid username and password combination
        if re.search('Invalid Username/password', response) or re.search('<title>Login :: TorrentLeech.org</title>', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True
