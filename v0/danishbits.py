import logging
import re

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class DanishbitsProvider:

    def __init__(self):

        self.session = Session()

        # Credentials
        self.username = None
        self.password = None

        # Torrent Stats
        self.minseed = 0
        self.minleech = 0
        self.freeleech = True

        # URLs
        self.url = 'https://danishbits.org/'
        self.urls = {
            'login': self.url + 'login.php',
            'search': self.url + 'torrents.php',
        }

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username.encode('utf-8'),
            'password': self.password.encode('utf-8'),
            'keeplogged': 1,
            'langlang': '',
            'login': 'Login',
        }

        response = self.session.post(self.urls['login'], data=login_params, returns='text')
        if not response:
            log.warn('Unable to connect to provider')
            self.session.cookies.clear()
            return False

        if '<title>Login :: Danishbits.org</title>' in response:
            log.warn('Invalid username or password. Check your settings')
            self.session.cookies.clear()
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {
            'action': 'newbrowse',
            'group': 3,
            'search': '',
        }

        def process_column_header(td):
            result = ''
            if td.img:
                result = td.img.get('title')
            if not result:
                result = td.get_text(strip=True)
            return result.encode('utf-8')

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_params['search'] = search_string

                data = self.session.get(self.urls['search'], params=search_params, returns='text')
                if not data:
                    log.debug('No data returned from provider')
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('table', id='torrent_table')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    # Literal:     Navn, Størrelse, Kommentarer, Tilføjet, Snatches, Seeders, Leechers
                    # Translation: Name, Size,      Comments,    Added,    Snatches, Seeders, Leechers
                    labels = [process_column_header(label) for label in torrent_rows[0]('td')]

                    # Skip column headers
                    for result in torrent_rows[1:]:

                        try:
                            title = result.find(class_='croptorrenttext').get_text(strip=True)
                            download_url = self.url + result.find(title='Direkte download link')['href']
                            if not all([title, download_url]):
                                continue

                            cells = result('td')

                            seeders = cells[labels.index('Seeders')].get_text(strip=True)
                            leechers = cells[labels.index('Leechers')].get_text(strip=True)

                            # Filter unseeded torrent
                            if seeders < self.minseed or leechers < self.minleech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            freeleech = result.find(class_='freeleech')
                            if self.freeleech and not freeleech:
                                continue

                            torrent_size = cells[labels.index('Størrelse')].contents[0]

                            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                            if mode != 'RSS':
                                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                            items.append(item)
                        except Exception:
                            continue

            results += items

        return results
