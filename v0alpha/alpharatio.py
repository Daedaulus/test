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


class AlphaRatioProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'http://alpharatio.cc/'
        self.urls = {
            'base': self.url,
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'torrents.php'),
        }

        # Credentials
        self.username = None
        self.password = None
        self.login_params = {
            'username': self.username,
            'password': self.password,
            'login': 'submit',
            'remember_me': 'on',
        }

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None

        # Search Params
        self.search_params = {
            'searchstr': '',
            'filter_cat[1]': 1,
            'filter_cat[2]': 1,
            'filter_cat[3]': 1,
            'filter_cat[4]': 1,
            'filter_cat[5]': 1
        }

        # Categories

        # Proper Strings
        self.proper_strings = [
            'PROPER',
            'REPACK',
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
            if td.a and td.a.img:
                col_header = td.a.img.get('title', td.a.get_text(strip=True))
            if not col_header:
                col_header = td.get_text(strip=True)
            return col_header

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}'.format(search=search_string.decode('utf-8')))

                search_params['searchstr'] = search_string
                search_url = self.urls['search']
                data = self.session.get(search_url, params=search_params).text
                if not data:
                    log.debug('No data returned from provider')
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('table', id='torrent_table')
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
                            title = cells[labels.index('Name /Year')].find('a', dir='ltr').get_text(strip=True)
                            download_url = urljoin(self.url, cells[labels.index('Name /Year')].find('a', title='Download')['href'])
                            if not all([title, download_url]):
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
        if re.search('Invalid Username/password', response) or re.search('<title>Login :: AlphaRatio.cc</title>', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    # Validate login
    def check_auth(self):
        raise NotImplementedError
