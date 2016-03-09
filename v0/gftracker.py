import logging
import re

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class GFTrackerProvider:

    def __init__(self):

        self.session = Session()

        # Credentials
        self.username = None
        self.password = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # URLs
        self.url = 'https://www.thegft.org/'
        self.urls = {
            'login': self.url + 'loginsite.php',
            'search': self.url + 'browse.php',
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for ' + self.name + ' are missing, check your config.')

        return True

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
        }

        # Initialize session with a GET to have cookies
        self.session.get(self.url, returns='text')
        response = self.session.post(self.urls['login'], data=login_params, returns='text')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        if re.search('Username or password incorrect', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):
        results = []
        if not self.login():
            return results

        # https://www.thegft.org/browse.php?view=0&c26=1&c37=1&c19=1&c47=1&c17=1&c4=1&search=arrow
        # Search Params
        search_params = {
            'view': 0,  # BROWSE
            'c4': 1,  # TV/XVID
            'c17': 1,  # TV/X264
            'c19': 1,  # TV/DVDRIP
            'c26': 1,  # TV/BLURAY
            'c37': 1,  # TV/DVDR
            'c47': 1,  # TV/SD
            'search': '',
        }

        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        def process_column_header(td):
            result = ''
            if td.a and td.a.img:
                result = td.a.img.get('title', td.a.get_text(strip=True))
            if not result:
                result = td.get_text(strip=True)
            return result

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
                    torrent_table = html.find('div', id='torrentBrowse')
                    torrent_rows = torrent_table.find_all('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    labels = [process_column_header(label) for label in torrent_rows[0].find_all('td')]

                    # Skip column headers
                    for result in torrent_rows[1:]:

                        try:
                            cells = result.find_all('td')

                            title = cells[labels.index('Name')].find('a').find_next('a')['title'] or cells[labels.index('Name')].find('a')['title']
                            download_url = self.url + cells[labels.index('DL')].find('a')['href']
                            if not all([title, download_url]):
                                continue

                            peers = cells[labels.index('S/L')].get_text(strip=True).split('/', 1)
                            seeders = peers[0]
                            leechers = peers[1]

                            # Filter unseeded torrent
                            if seeders < self.minseed or leechers < self.minleech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            torrent_size = cells[labels.index('Size/Snatched')].get_text(strip=True).split('/', 1)[0]

                            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                            if mode != 'RSS':
                                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                            items.append(item)
                        except Exception:
                            continue

            results += items

        return results
