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


class PhxBitProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'https://phxbit.com/'
        self.urls = {
            'base': self.url,
            'login': urljoin(self.url, 'connect.php'),
            'search': urljoin(self.url, 'sphinx.php')
        }

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

        # Search Params
        self.search_params = {
            'order': 'desc',
            'sort': 'normal',
            'group': 'series'
        }

        # Categories

        # Proper Strings
        self.proper_strings = [
            'PROPER',
        ]

        # Options

    # Search page
    def search(
        self,
        search_strings,
        search_params,
        torrent_method=None,
        ep_obj=None,
        *args, **kwargs
    ):
        results = []

        if not self.login():
            return results

        def process_column_header(td):
            col_header = ''
            if td.img:
                col_header = td.img.get('alt', '')
            if not col_header:
                col_header = td.get_text(strip=True)
            return col_header

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    # Use exact=1 parameter if we're doing a backlog or manual search
                    search_params['exact'] = 1
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_params['q'] = search_string
                data = self.session.get(self.urls['search'], params=search_params).text
                if not data:
                    log.debug('No data returned from provider')
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('table')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    labels = [process_column_header(label) for label in torrent_rows[0]('td')]

                    # Skip column headers
                    for result in torrent_rows[1:]:
                        cells = result('td')
                        if len(cells) < len(labels):
                            continue

                        try:
                            title = cells[labels.index('Nom')].get_text(strip=True)
                            download_url = cells[labels.index('DL')].find('a')['href']
                            if not all([title, download_url]):
                                continue

                            seeders = cells[labels.index('Seed')].get_text(strip=True)
                            leechers = cells[labels.index('Leech')].get_text(strip=True)

                            # Filter unseeded torrent
                            if seeders < self.min_seed or leechers < self.min_leech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            torrent_size = cells[labels.index('Taille')].get_text(strip=True)

                            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}

                            if mode != 'RSS':
                                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                            items.append(item)

                        except Exception:
                            continue

            results += items

        return results

    # Parse page for results
    def parse(self):
        raise NotImplementedError

    # Log in
    def login(self, login_params):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        response = self.session.post(self.urls['login'], data=login_params).text
        if not response:
            log.warn('Unable to connect to provider')
            return False

        # Invalid username and password combination
        if not re.search('dons.php', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    # Validate login
    def check_auth(self):
        raise NotImplementedError
