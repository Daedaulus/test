import logging

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class T411Provider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        TorrentProvider.__init__(self, 'T411')

        self.username = None
        self.password = None
        self.token = None
        self.tokenLastUpdate = None

        self.cache = tvcache.TVCache(self, min_time=10)  # Only poll T411 every 10 minutes max

        self.urls = {'base_url': 'http://www.t411.ch/',
                     'search': 'https://api.t411.ch/torrents/search/%s*?cid=%s&limit=100',
                     'rss': 'https://api.t411.ch/torrents/top/today',
                     'login_page': 'https://api.t411.ch/auth',
                     'download': 'https://api.t411.ch/torrents/download/%s'}

        self.url = self.urls['base_url']

        self.headers.update({'User-Agent': USER_AGENT})

        self.subcategories = [433, 637, 455, 639]

        self.minseed = 0
        self.minleech = 0
        self.confirmed = False

    def login(self):

        if self.token is not None:
            if time.time() < (self.tokenLastUpdate + 30 * 60):
                return True

        login_params = {'username': self.username,
                        'password': self.password}

        response = self.get_url(self.urls['login_page'], post_data=login_params, returns='json')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        if response and 'token' in response:
            self.token = response['token']
            self.tokenLastUpdate = time.time()
            # self.uid = response['uid'].encode('ascii', 'ignore')
            self.session.auth = T411Auth(self.token)
            return True
        else:
            log.warn('Token not found in authentication response')
            return False

    def search(self, search_params, age=0, ep_obj=None):  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        results = []
        if not self.login():
            return results

        for mode in search_params:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_params[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_urlS = ([self.urls['search'] % (search_string, u) for u in self.subcategories], [self.urls['rss']])[mode == 'RSS']
                for search_url in search_urlS:
                    data = self.get_url(search_url, returns='json')
                    if not data:
                        continue

                    try:
                        if 'torrents' not in data and mode != 'RSS':
                            log.debug('Data returned from provider does not contain any torrents')
                            continue

                        torrents = data['torrents'] if mode != 'RSS' else data

                        if not torrents:
                            log.debug('Data returned from provider does not contain any torrents')
                            continue

                        for torrent in torrents:
                            if mode == 'RSS' and 'category' in torrent and try_int(torrent['category'], 0) not in self.subcategories:
                                continue

                            try:
                                title = torrent['name']
                                torrent_id = torrent['id']
                                download_url = (self.urls['download'] % torrent_id).encode('utf8')
                                if not all([title, download_url]):
                                    continue

                                seeders = try_int(torrent['seeders'])
                                leechers = try_int(torrent['leechers'])
                                verified = bool(torrent['isVerified'])
                                torrent_size = torrent['size']

                                # Filter unseeded torrent
                                if seeders < self.minseed or leechers < self.minleech:
                                    if mode != 'RSS':
                                        log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                    continue

                                if self.confirmed and not verified and mode != 'RSS':
                                    log.debug('Found result ' + title + ' but that doesn\'t seem like a verified result so I\'m ignoring it')
                                    continue

                                size = convert_size(torrent_size) or -1
                                item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                                if mode != 'RSS':
                                    log.debug('Found result: %s with %s seeders and %s leechers' % (title, seeders, leechers))

                                items.append(item)

                            except Exception:
                                log.debug('Invalid torrent data, skipping result: %s' % torrent)
                                log.debug('Failed parsing provider. Traceback: %s' % traceback.format_exc())
                                continue

                    except Exception:
                        log.error('Failed parsing provider. Traceback: %s' % traceback.format_exc())

            # For each search mode sort all the items by seeders if available if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)

            results += items

        return results


class T411Auth(AuthBase):  # pylint: disable=too-few-public-methods
    """Attaches HTTP Authentication to the given Request object."""
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = self.token
        return r

provider = T411Provider()
