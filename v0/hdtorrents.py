import logging
import re

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class HDTorrentsProvider:

    def __init__(self):

        self.session = Session()

        # Credentials
        self.username = None
        self.password = None
        self.minseed = None
        self.minleech = None
        self.freeleech = None

        self.urls = {'base_url': 'https://hd-torrents.org',
                     'login': 'https://hd-torrents.org/login.php',
                     'search': 'https://hd-torrents.org/torrents.php?search=%s&active=1&options=0%s',
                     'rss': 'https://hd-torrents.org/torrents.php?search=&active=1&options=0%s',
                     'home': 'https://hd-torrents.org/%s'}

        self.url = self.urls['base_url']

        self.categories = '&category[]=59&category[]=60&category[]=30&category[]=38'
        self.proper_strings = ['PROPER', 'REPACK']

    def _check_auth(self):

        if not self.username or not self.password:
            log.warn('Invalid username or password. Check your settings')

        return True

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {'uid': self.username,
                        'pwd': self.password,
                        'submit': 'Confirm'}

        response = self.session.post(self.urls['login'], data=login_params, returns='text')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        if re.search('You need cookies enabled to log in.', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):
        results = []
        if not self.login():
            return results

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    search_url = self.urls['search'] % (quote_plus(search_string), self.categories)
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))
                else:
                    search_url = self.urls['rss'] % self.categories

                if self.freeleech:
                    search_url = search_url.replace('active=1', 'active=5')

                data = self.session.get(search_url, returns='text')
                if not data or 'please try later' in data:
                    log.debug('No data returned from provider')
                    continue

                if data.find('No torrents here') != -1:
                    log.debug('Data returned from provider does not contain any torrents')
                    continue

                # Search result page contains some invalid html that prevents html parser from returning all data.
                # We cut everything before the table that contains the data we are interested in thus eliminating
                # the invalid html portions
                try:
                    index = data.lower().index('<table class='mainblockcontenttt'')
                except ValueError:
                    log.debug('Could not find table of torrents mainblockcontenttt')
                    continue

                data = data[index:]

                with BS4Parser(data, 'html5lib') as html:
                    if not html:
                        log.debug('No html data parsed from provider')
                        continue

                    torrent_rows = []
                    torrent_table = html.find('table', class_='mainblockcontenttt')
                    if torrent_table:
                        torrent_rows = torrent_table('tr')

                    if not torrent_rows:
                        log.debug('Could not find results in returned data')
                        continue

                    # Cat., Active, Filename, Dl, Wl, Added, Size, Uploader, S, L, C
                    labels = [label.a.get_text(strip=True) if label.a else label.get_text(strip=True) for label in torrent_rows[0]('td')]

                    # Skip column headers
                    for result in torrent_rows[1:]:
                        try:
                            cells = result.findChildren('td')[:len(labels)]
                            if len(cells) < len(labels):
                                continue

                            title = cells[labels.index('Filename')].a.get_text(strip=True)
                            seeders = cells[labels.index('S')].get_text(strip=True)
                            leechers = cells[labels.index('L')].get_text(strip=True)
                            torrent_size = cells[labels.index('Size')].get_text()

                            download_url = self.url + '/' + cells[labels.index('Dl')].a['href']
                        except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                            continue

                        if not all([title, download_url]):
                            continue

                        # Filter unseeded torrent
                        if seeders < self.minseed or leechers < self.minleech:
                            if mode != 'RSS':
                                log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                            continue

                        item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                        if mode != 'RSS':
                            log.debug('Found result: %s with %s seeders and %s leechers' % (title, seeders, leechers))

                        items.append(item)

            results += items

        return results
