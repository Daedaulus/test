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


class TorrentBytesProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'https://www.torrentbytes.net/'
        self.urls = {
            'base': self.url,
            'login': urljoin(self.url, 'takelogin.php'),
            'search': urljoin(self.url, 'browse.php')
        }

        # Credentials
        self.username = None
        self.password = None
        self.login_params = {
            'username': self.username,
            'password': self.password,
            'login': 'Log in!'
        }

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None
        self.freeleech = False

        # Search Params
        self.search_params = {
            'c41': 1,
            'c33': 1,
            'c38': 1,
            'c32': 1,
            'c37': 1
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
                    torrent_table = html.find('table', border='1')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    labels = [label.get_text(strip=True) for label in torrent_rows[0]('td')]

                    # Skip column headers
                    for result in torrent_rows[1:]:
                        try:
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

                        except (AttributeError, TypeError):
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
        if re.search('Username or password incorrect', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    # Validate login
    def check_auth(self):
        raise NotImplementedError
