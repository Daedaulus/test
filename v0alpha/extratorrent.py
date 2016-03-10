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


class ExtraTorrentProvider:

    def __init__(self):

        self.session = Session()

        # Credentials
        self.public = True

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None

        # URLs
        self.urls = {
            'index': 'http://extratorrent.cc',
            'rss': 'http://extratorrent.cc/rss.xml',
        }
        self.url = self.urls['index']
        self.custom_url = None

        # Proper Strings

        # Search Params
        self.search_params = {
            'cid': 8,
        }

    def search(self, search_strings, torrent_method):
        results = []

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                self.search_params.update({'type': ('search', 'rss')[mode == 'RSS'], 'search': search_string})
                search_url = self.urls['rss'] if not self.custom_url else self.urls['rss'].replace(self.urls['index'], self.custom_url)
                data = self.session.get(search_url, params=self.search_params).text
                if not data:
                    log.debug('No data returned from provider')
                    continue

                if not data.startswith('<?xml'):
                    log.info('Expected xml but got something else, is your mirror failing?')
                    continue

                with BS4Parser(data, 'html5lib') as parser:
                    for item in parser.findAll('item'):
                        try:
                            title = re.sub(r'^<!\[CDATA\[|\]\]>$', '', item.find('title').get_text(strip=True))
                            seeders = item.find('seeders').get_text(strip=True)
                            leechers = item.find('leechers').get_text(strip=True)
                            torrent_size = item.find('size').get_text()

                            if torrent_method == 'blackhole':
                                enclosure = item.find('enclosure')  # Backlog doesnt have enclosure
                                download_url = enclosure['url'] if enclosure else item.find('link').next.strip()
                                download_url = re.sub(r'(.*)/torrent/(.*).html', r'\1/download/\2.torrent', download_url)
                            else:
                                info_hash = item.find('info_hash').get_text(strip=True)
                                download_url = 'magnet:?xt=urn:btih:' + info_hash + '&dn=' + title + self._custom_trackers

                        except (AttributeError, TypeError, KeyError, ValueError):
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
