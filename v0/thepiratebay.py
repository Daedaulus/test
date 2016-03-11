import logging
import re

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class ThePirateBayProvider:

    def __init__(self):

        self.session = Session()

        # Credentials
        self.public = True

        # Torrent Stats
        self.minseed = None
        self.minleech = None
        self.confirmed = True

        # URLs
        self.url = 'https://thepiratebay.se'
        self.urls = {
            'rss': urljoin(self.url, 'browse/200'),
            'search': urljoin(self.url, 's/'),  # Needs trailing /
        }
        self.custom_url = None

    def search(self, search_strings, age=0, ep_obj=None):
        results = []

        search_params = {
            'q': '',
            'type': 'search',
            'orderby': 7,
            'page': 0,
            'category': 200
        }

        def process_column_header(th):
            result = ''
            if th.a:
                result = th.a.get_text(strip=True)
            if not result:
                result = th.get_text(strip=True)
            return result

        for mode in search_strings:
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

                    data = self.session.get(search_url, params=search_params, returns='text')
                else:
                    data = self.session.get(search_url, returns='text')

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
                            if seeders < self.minseed or leechers < self.minleech:
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
