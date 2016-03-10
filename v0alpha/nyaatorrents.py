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


class NyaaProvider:

    def __init__(self):

        self.session = Session()

        # Credentials
        self.public = True
        self.supports_absolute_numbering = True
        self.anime_only = True

        # Torrent Stats
        self.min_seed = 0
        self.min_leech = 0
        self.confirmed = False

        # URLs
        self.url = 'http://www.nyaa.se'

        # Miscellaneous
        self.regex = re.compile(r'(\d+) seeder\(s\), (\d+) leecher\(s\), \d+ download\(s\) - (\d+.?\d* [KMGT]iB)(.*)', re.DOTALL)

    def search(self, search_strings):
        results = []

        if self.show and not self.show.is_anime:
            return results

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_params = {
                    'page': 'rss',
                    'cats': '1_0',  # All anime
                    'sort': 2,  # Sort Descending By Seeders
                    'order': 1
                }
                if mode != 'RSS':
                    search_params['term'] = search_string

                results = []
                data = self.cache.getRSSFeed(self.url, params=search_params)['entries']
                if not data:
                    log.debug('Data returned from provider does not contain any torrents')

                for curItem in data:
                    try:
                        title = curItem['title']
                        download_url = curItem['link']
                        if not all([title, download_url]):
                            continue

                        item_info = self.regex.search(curItem['summary'])
                        if not item_info:
                            log.debug('There was a problem parsing an item summary, skipping: {}'.format(title))
                            continue

                        seeders, leechers, torrent_size, verified = item_info.groups()

                        if seeders < self.min_seed or leechers < self.min_leech:
                            if mode != 'RSS':
                                log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                            continue

                        if self.confirmed and not verified and mode != 'RSS':
                            log.debug('Found result {} but that doesn\'t seem like a verified result so I\'m ignoring it'.format(title))
                            continue

                        result = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers}

                        if mode != 'RSS':
                            log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                        items.append(result)

                    except Exception:
                        continue

            results += items

        return results
