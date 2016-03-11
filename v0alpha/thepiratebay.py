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


class ThePirateBayProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'https://thepiratebay.se/'
        self.urls = {
            'base': self.url,
            'rss': urljoin(self.url, 'browse/200'),
            'search': urljoin(self.url, 's/'),  # Needs trailing /
        }
        self.custom_url = None

        # Credentials
        self.public = True

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None
        self.confirmed = True

        # Proper Strings

        # Search Params
        self.search_params = {
            'q': '',
            'type': 'search',
            'orderby': 7,
            'page': 0,
            'category': 200
        }

        # Categories

        # Proper Strings

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

        def process_column_header(th):
            col_header = ''
            if th.a:
                col_header = th.a.get_text(strip=True)
            if not col_header:
                col_header = th.get_text(strip=True)
            return col_header

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:
                search_url = self.urls['search'] if mode != 'RSS' else self.urls['rss']
                if self.custom_url:
                    if not validators.url(self.custom_url):
                        log.warn('Invalid custom url: {}'.format(self.custom_url))
                        return results
                    search_url = urljoin(self.custom_url, search_url.split(self.url)[1])

                if mode != 'RSS':
                    search_params['q'] = search_string
                    log.debug('Search string: {search}'.format(search=search_string.decode('utf-8')))

                    data = self.session.get(search_url, params=search_params).text
                else:
                    data = self.session.get(search_url).text
                if not data:
                    log.debug('URL did not return data, maybe try a custom url, or a different one')
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('table', id='searchResult')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    labels = [process_column_header(label) for label in torrent_rows[0]('th')]

                    # Skip column headers
                    for result in torrent_rows[1:]:
                        try:
                            cells = result('td')

                            title = result.find(class_='detName').get_text(strip=True)
                            download_url = result.find(title='Download this torrent using magnet')['href'] + self._custom_trackers
                            if 'magnet:?' not in download_url:
                                log.debug('Invalid ThePirateBay proxy please try another one')
                                continue
                            if not all([title, download_url]):
                                continue

                            seeders = cells[labels.index('SE')].get_text(strip=True)
                            leechers = cells[labels.index('LE')].get_text(strip=True)

                            # Filter unseeded torrent
                            if seeders < self.min_seed or leechers < self.min_leech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            # Accept Torrent only from Good People for every Episode Search
                            if self.confirmed and not result.find(alt=re.compile(r'VIP|Trusted')):
                                if mode != 'RSS':
                                    log.debug('Found result {} but that doesn\'t seem like a trusted result so I\'m ignoring it'.format(title))
                                continue

                            torrent_size = cells[labels.index('Name')].find(class_='detDesc').get_text(strip=True).split(', ')[1]
                            torrent_size = re.sub(r'Size ([\d.]+).+([KMGT]iB)', r'\1 \2', torrent_size)

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
        raise NotImplementedError

    # Validate login
    def check_auth(self):
        raise NotImplementedError
