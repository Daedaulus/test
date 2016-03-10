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


class BTDiggProvider:

    def __init__(self):

        self.session = Session()

        # Credentials
        self.public = True

        # Torrent Stats

        # URLs
        self.url = 'https://btdigg.org'
        self.urls = {
            'api': 'https://api.btdigg.org/api/private-341ada3245790954/s02',
        }

        # Proper Strings
        self.proper_strings = [
            'PROPER',
            'REPACK',
        ]

        # Search Params

    def search(self, search_strings):
        results = []

        # Search Params
        search_params = {
            'p': 0
        }

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:
                search_params['q'] = search_string

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))
                    search_params['order'] = 0
                else:
                    search_params['order'] = 2

                jdata = self.session.get(self.urls['api'], params=search_params).json()
                if not jdata:
                    log.debug('No data returned from provider')
                    continue

                for torrent in jdata:
                    try:
                        title = torrent.pop('name', '')
                        download_url = torrent.pop('magnet') + self._custom_trackers if torrent['magnet'] else None
                        if not all([title, download_url]):
                            continue

                        if float(torrent.pop('ff')):
                            log.debug('Ignoring result for {} since it\'s been reported as fake (level = {})'.format(title, torrent['ff']))
                            continue

                        if not int(torrent.pop('files')):
                            log.debug('Ignoring result for {} because it has no files'.format(title))
                            continue

                        # Provider doesn't provide seeders/leechers
                        seeders = 1
                        leechers = 0

                        torrent_size = torrent.pop('size')

                        item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}

                        if mode != 'RSS':
                                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                        items.append(item)

                    except Exception:
                        continue

            results += items

        return results
