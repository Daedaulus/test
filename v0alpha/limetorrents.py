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


class LimeTorrentsProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'https://www.limetorrents.cc/'
        self.urls = {
            'base': self.url,
            'index': self.url,
            'search': urljoin(self.url, 'searchrss/20/'),
            'rss': urljoin(self.url, 'rss/20/'),
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

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                try:
                    search_url = (self.urls['rss'], self.urls['search'] + search_string)[mode != 'RSS']

                    data = self.session.get(search_url).text
                    if not data:
                        log.debug('No data returned from provider')
                        continue

                    if not data.startswith('<?xml'):
                        log.info('Expected xml but got something else, is your mirror failing?')
                        continue

                    data = BS4Parser(data, 'html5lib')

                    entries = data.findAll('item')
                    if not entries:
                        log.info('Returned xml contained no results')
                        continue

                    for item in entries:
                        try:
                            title = item.title.text
                            # Use the itorrents link limetorrents provides,
                            # unless it is not itorrents or we are not using blackhole
                            # because we want to use magnets if connecting direct to client
                            # so that proxies work.
                            download_url = item.enclosure['url']
                            if torrent_method != 'blackhole' or 'itorrents' not in download_url:
                                download_url = item.enclosure['url']
                                # http://itorrents.org/torrent/C7203982B6F000393B1CE3A013504E5F87A46A7F.torrent?title=The-Night-of-the-Generals-(1967)[BRRip-1080p-x264-by-alE13-DTS-AC3][Lektor-i-Napisy-PL-Eng][Eng]
                                # Keep the hash a separate string for when its needed for failed
                                torrent_hash = re.match(r'(.*)([A-F0-9]{40})(.*)', download_url, re.IGNORECASE).group(2)
                                download_url = 'magnet:?xt=urn:btih:' + torrent_hash + '&dn=' + title + self._custom_trackers

                            if not (title and download_url):
                                continue
                            # seeders and leechers are presented diferently when doing a search and when looking for newly added
                            if mode == 'RSS':
                                # <![CDATA[
                                # Category: <a href='http://www.limetorrents.cc/browse-torrents/TV-shows/'>TV shows</a><br /> Seeds: 1<br />Leechers: 0<br />Size: 7.71 GB<br /><br /><a href='http://www.limetorrents.cc/Owen-Hart-of-Gold-Djon91-torrent-7180661.html'>More @ limetorrents.cc</a><br />
                                # ]]>
                                description = item.find('description')
                                seeders = description('br')[0].next_sibling.strip().lstrip('Seeds: ')
                                leechers = description('br')[1].next_sibling.strip().lstrip('Leechers: ')
                            else:
                                # <description>Seeds: 6982 , Leechers 734</description>
                                description = item.find('description').text.partition(',')
                                seeders = description[0].lstrip('Seeds: ').strip()
                                leechers = description[2].lstrip('Leechers ').strip()

                            torrent_size = item.find('size').text

                        except (AttributeError, TypeError, KeyError, ValueError):
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
