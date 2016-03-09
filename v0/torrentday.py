import logging

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class TorrentDayProvider:

    def __init__(self):

        self.session = Session()

        # Credentials
        self.username = None
        self.password = None
        self._uid = None
        self._hash = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None
        self.freeleech = False

        # URLs
        self.url = 'https://classic.torrentday.com'
        self.urls = {
            'login': urljoin(self.url, '/torrents/'),
            'search': urljoin(self.url, '/V3/API/API.php'),
            'download': urljoin(self.url, '/download.php/')
        }

        self.cookies = None
        self.categories = {'Season': {'c14': 1}, 'Episode': {'c2': 1, 'c26': 1, 'c7': 1, 'c24': 1},
                           'RSS': {'c2': 1, 'c26': 1, 'c7': 1, 'c24': 1, 'c14': 1}}

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        if self._uid and self._hash:
            add_dict_to_cookiejar(self.session.cookies, self.cookies)
        else:

            login_params = {
                'username': self.username,
                'password': self.password,
                'submit.x': 0,
                'submit.y': 0
            }

            response = self.session.post(self.urls['login'], data=login_params, returns='text')
            if not response:
                log.warn('Unable to connect to provider')
                return False

            if re.search('You tried too often', response):
                log.warn('Too many login access attempts')
                return False

            try:
                if dict_from_cookiejar(self.session.cookies)['uid'] and dict_from_cookiejar(self.session.cookies)['pass']:
                    self._uid = dict_from_cookiejar(self.session.cookies)['uid']
                    self._hash = dict_from_cookiejar(self.session.cookies)['pass']
                    self.cookies = {'uid': self._uid,
                                    'pass': self._hash}
                    return True
            except Exception:
                pass

            log.warn('Unable to obtain cookie')
            return False

    def search(self, search_params, age=0, ep_obj=None):
        results = []
        if not self.login():
            return results

        for mode in search_params:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_params[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_string = '+'.join(search_string.split())

                post_data = dict({'/browse.php?': None, 'cata': 'yes', 'jxt': 8, 'jxw': 'b', 'search': search_string},
                                 **self.categories[mode])

                if self.freeleech:
                    post_data.update({'free': 'on'})

                parsedJSON = self.session.get(self.urls['search'], post_data=post_data, returns='json')
                if not parsedJSON:
                    log.debug('No data returned from provider')
                    continue

                try:
                    torrents = parsedJSON.get('Fs', [])[0].get('Cn', {}).get('torrents', [])
                except Exception:
                    log.debug('Data returned from provider does not contain any torrents')
                    continue

                for torrent in torrents:

                    title = re.sub(r'\[.*\=.*\].*\[/.*\]', '', torrent['name']) if torrent['name'] else None
                    download_url = urljoin(self.urls['download'], '{}/{}'.format(torrent['id'], torrent['fname'])) if torrent['id'] and torrent['fname'] else None

                    if not all([title, download_url]):
                        continue

                    seeders = int(torrent['seed']) if torrent['seed'] else 1
                    leechers = int(torrent['leech']) if torrent['leech'] else 0

                    # Filter unseeded torrent
                    if seeders < self.minseed or leechers < self.minleech:
                        if mode != 'RSS':
                            log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                        continue

                    torrent_size = torrent['size']

                    item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}

                    if mode != 'RSS':
                        log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                    items.append(item)

            results += items

        return results
