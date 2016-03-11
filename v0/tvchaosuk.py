import logging
import re

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class TVChaosUKProvider:

    def __init__(self):

        self.session = Session()

        # Credentials
        self.username = None
        self.password = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None
        self.freeleech = None

        # URLs
        self.url = 'https://www.tvchaosuk.com/'
        self.urls = {
            'login': self.url + 'takelogin.php',
            'index': self.url + 'index.php',
            'search': self.url + 'browse.php'
        }

    def _check_auth(self):
        if self.username and self.password:
            return True

        raise Exception('Your authentication credentials for ' + self.name + ' are missing, check your config.')

    def login(self):
        if len(self.session.cookies) >= 4:
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'logout': 'no',
            'submit': 'LOGIN',
            'returnto': '/browse.php'
        }

        response = self.session.post(self.urls['login'], data=login_params, returns='text')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        if re.search('Error: Username or password incorrect!', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {
            'do': 'search',
            'search_type': 't_name',
            'category': 0,
            'include_dead_torrents': 'no',
            'submit': 'search'
        }

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:

                if mode == 'Season':
                    search_string = re.sub(r'(.*)Season', r'\1Series', search_string)

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string))

                search_params['keywords'] = search_string
                data = self.session.get(self.urls['search'], post_data=search_params, returns='text')
                if not data:
                    log.debug('No data returned from provider')
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find(id='sortabletable')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    labels = [label.img['title'] if label.img else label.get_text(strip=True) for label in torrent_rows[0]('td')]
                    for torrent in torrent_rows[1:]:
                        try:
                            if self.freeleech and not torrent.find('img', alt=re.compile('Free Torrent')):
                                continue

                            title = torrent.find(class_='tooltip-content').div.get_text(strip=True).replace('mp4', 'x264')
                            download_url = torrent.find(title='Click to Download this Torrent!').parent['href']
                            if not all([title, download_url]):
                                continue

                            seeders = torrent.find(title='Seeders').get_text(strip=True)
                            leechers = torrent.find(title='Leechers').get_text(strip=True)

                            # Filter unseeded torrent
                            if seeders < self.minseed or leechers < self.minleech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            # Chop off tracker/channel prefix or we cant parse the result!
                            if mode != 'RSS' and search_params['keywords']:
                                show_name_first_word = re.search(r'^[^ .]+', search_params['keywords']).group()
                                if not title.startswith(show_name_first_word):
                                    title = re.sub(r'.*(' + show_name_first_word + '.*)', r'\1', title)

                            # Change title from Series to Season, or we can't parse
                            if mode == 'Season':
                                title = re.sub(r'(.*)(?i)Series', r'\1Season', title)

                            # Strip year from the end or we can't parse it!
                            title = re.sub(r'(.*)[\. ]?\(\d{4}\)', r'\1', title)
                            title = re.sub(r'\s+', r' ', title)

                            torrent_size = torrent('td')[labels.index('Size')].get_text(strip=True)

                            if mode != 'RSS':
                                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers}
                            items.append(item)
                        except Exception:
                            continue

            results += items

        return results
