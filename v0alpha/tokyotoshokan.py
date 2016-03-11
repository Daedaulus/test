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


class TokyoToshokanProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'http://tokyotosho.info/'
        self.urls = {
            'base': self.url,
            'search': urljoin(self.url, 'search.php'),
            'rss': urljoin(self.url, 'rss.php'),
        }

        # Credentials
        self.public = True

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None
        self.supports_absolute_numbering = True
        self.anime_only = True

        # Search Params

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
        if not self.show or not self.show.is_anime:
            return results

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_params = {
                    'terms': search_string,
                    'type': 1,  # get anime types
                }
                data = self.session.get(self.urls['search'], params=search_params).text
                if not data:
                    log.debug('No data returned from provider')
                    continue

                with BS4Parser(data, 'html5lib') as soup:
                    torrent_table = soup.find('table', class_='listing')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    a = 1 if len(torrent_rows[0]('td')) < 2 else 0

                    for top, bot in zip(torrent_rows[a::2], torrent_rows[a + 1::2]):
                        try:
                            desc_top = top.find('td', class_='desc-top')
                            title = desc_top.get_text(strip=True)
                            download_url = desc_top.find('a')['href']

                            desc_bottom = bot.find('td', class_='desc-bot').get_text(strip=True)
                            torrent_size = desc_bottom.split('|')[1].strip('Size: ')

                            stats = bot.find('td', class_='stats').get_text(strip=True)
                            sl = re.match(r'S:(?P<seeders>\d+)L:(?P<leechers>\d+)C:(?:\d+)ID:(?:\d+)', stats.replace(' ', ''))
                            seeders = sl.group('seeders') if sl else 0
                            leechers = sl.group('leechers') if sl else 0
                        except Exception:
                            continue

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
