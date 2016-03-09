import logging
import re

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class KatProvider:

    def __init__(self):

        self.session = Session()

        self.public = True

        self.confirmed = True
        self.minseed = None
        self.minleech = None

        self.url = 'https://kat.cr'
        self.urls = {'search': urljoin(self.url, '%s/')}

        self.custom_url = None

    def search(self, search_strings, age=0, ep_obj=None):
        results = []

        anime = (self.show and self.show.anime) or (ep_obj and ep_obj.show and ep_obj.show.anime) or False
        search_params = {
            'q': '',
            'field': 'seeders',
            'sorder': 'desc',
            'rss': 1,
            'category': ('tv', 'anime')[anime]
        }

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:

                search_params['q'] = search_string if mode != 'RSS' else ''
                search_params['field'] = 'seeders' if mode != 'RSS' else 'time_add'

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_url = self.urls['search'] % ('usearch' if mode != 'RSS' else search_string)
                if self.custom_url:
                    if not validators.url(self.custom_url):
                        log.warn('Invalid custom url: {}'.format(self.custom_url))
                        return results
                    search_url = urljoin(self.custom_url, search_url.split(self.url)[1])

                data = self.session.get(search_url, params=search_params, returns='text')
                if not data:
                    log.debug('URL did not return data, maybe try a custom url, or a different one')
                    continue

                if not data.startswith('<?xml'):
                    log.info('Expected xml but got something else, is your mirror failing?')
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    for item in html.find_all('item'):
                        try:
                            title = item.title.get_text(strip=True)
                            # Use the torcache link kat provides,
                            # unless it is not torcache or we are not using blackhole
                            # because we want to use magnets if connecting direct to client
                            # so that proxies work.
                            download_url = item.enclosure['url']
                            if sickbeard.TORRENT_METHOD != 'blackhole' or 'torcache' not in download_url:
                                download_url = item.find('torrent:magneturi').next.replace('CDATA', '').strip('[!]') + self._custom_trackers

                            if not (title and download_url):
                                continue

                            seeders = item.find('torrent:seeds').get_text(strip=True)
                            leechers = item.find('torrent:peers').get_text(strip=True)

                            # Filter unseeded torrent
                            if seeders < self.minseed or leechers < self.minleech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            verified = bool(int(item.find('torrent:verified').get_text(strip=True)))
                            if self.confirmed and not verified:
                                if mode != 'RSS':
                                    log.debug('Found result ' + title + ' but that doesn\'t seem like a verified result so I\'m ignoring it')
                                continue

                            torrent_size = item.find('torrent:contentlength').get_text(strip=True)
                            info_hash = item.find('torrent:infohash').get_text(strip=True)

                            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': info_hash}
                            if mode != 'RSS':
                                log.debug('Found result: %s with %s seeders and %s leechers' % (title, seeders, leechers))

                            items.append(item)

                        except (AttributeError, TypeError, KeyError, ValueError):
                            continue

            results += items

        return results
