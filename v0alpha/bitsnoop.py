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


class BitSnoopProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'http://bitsnoop.com/'
        self.urls = {
            'base': self.url,
            'index': self.url,
            'search': urljoin(self.url, 'search/video/'),
            'rss': urljoin(self.url, 'new_video.html?fmt=rss'),
        }

        # Credentials
        self.public = True

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None

        # Search Params

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

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                try:
                    search_url = (self.urls['rss'], self.urls['search'] + search_string + '/s/d/1/?fmt=rss')[mode != 'RSS']
                    data = self.session.get(search_url).text
                    if not data:
                        log.debug('No data returned from provider')
                        continue

                    if not data.startswith('<?xml'):
                        log.info('Expected xml but got something else, is your mirror failing?')
                        continue

                    data = BS4Parser(data, 'html5lib')
                    for item in data.findAll('item'):
                        try:
                            if not item.category.text.endswith(('TV', 'Anime')):
                                continue

                            title = item.title.text
                            # # For PY2:
                            # assert isinstance(title, unicode)

                            # Use the torcache link bitsnoop provides,
                            # unless it is not torcache or we are not using blackhole
                            # because we want to use magnets if connecting direct to client
                            # so that proxies work.
                            download_url = item.enclosure['url']
                            if torrent_method != 'blackhole' or 'torcache' not in download_url:
                                download_url = item.find('magneturi').next.replace('CDATA', '').strip('[]') + self._custom_trackers

                            if not (title and download_url):
                                continue

                            seeders = item.find('numseeders').text
                            leechers = item.find('numleechers').text
                            torrent_size = item.find('size').text

                            info_hash = item.find('infohash').text

                        except (AttributeError, TypeError, KeyError, ValueError):
                            continue

                            # Filter unseeded torrent
                        if seeders < self.min_seed or leechers < self.min_leech:
                            if mode != 'RSS':
                                log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                            continue

                        item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': info_hash}

                        if mode != 'RSS':
                                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                        items.append(item)

                except (AttributeError, TypeError, KeyError, ValueError):
                    log.error('Failed parsing provider. Traceback: %r' % traceback.format_exc())

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
