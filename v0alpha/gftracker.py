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


class GFTrackerProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'https://www.thegft.org/'
        self.urls = {
            'base': self.url,
            'login': urljoin(self.url, 'loginsite.php'),
            'search': urljoin(self.url, 'browse.php'),
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
            'view': 0,  # BROWSE
            'c4': 1,  # TV/XVID
            'c17': 1,  # TV/X264
            'c19': 1,  # TV/DVDRIP
            'c26': 1,  # TV/BLURAY
            'c37': 1,  # TV/DVDR
            'c47': 1,  # TV/SD
            'search': '',
        }

        # Categories

        # Proper Strings
        self.proper_strings = [
            'PROPER',
            'REPACK',
            'REAL',
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
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_params['search'] = search_string
                data = self.session.get(self.urls['search'], params=search_params).text
                if not data:
                    log.debug('No data returned from provider')
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('div', id='torrentBrowse')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    labels = [process_column_header(label) for label in torrent_rows[0]('td')]

                    # Skip column headers
                    for result in torrent_rows[1:]:

                        try:
                            cells = result('td')

                            title = cells[labels.index('Name')].find('a').find_next('a')['title'] or cells[labels.index('Name')].find('a')['title']
                            download_url = self.url + cells[labels.index('DL')].find('a')['href']
                            if not all([title, download_url]):
                                continue

                            peers = cells[labels.index('S/L')].get_text(strip=True).split('/', 1)
                            seeders = peers[0]
                            leechers = peers[1]

                            # Filter unseeded torrent
                            if seeders < self.min_seed or leechers < self.min_leech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            torrent_size = cells[labels.index('Size/Snatched')].get_text(strip=True).split('/', 1)[0]

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

        # Initialize session with a GET to have cookies
        self.session.get(self.url)
        response = self.session.post(self.urls['login'], data=login_params).text
        if not response:
            log.warn('Unable to connect to provider')
            return False

        # Invalid username and password combination
        if re.search('Username or password incorrect', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    # Validate login
    def check_auth(self):
        if not self.username or not self.password:
            raise Exception('Your authentication credentials for ' + self.name + ' are missing, check your config.')
        return True
