import logging

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class NorbitsProvider:

    def __init__(self):

        self.session = Session()

        # Credentials
        self.username = None
        self.passkey = None
        self.minseed = None
        self.minleech = None

        self.url = 'https://norbits.net'
        self.urls = {'search': self.url + '/api2.php?action=torrents',
                     'download': self.url + '/download.php?'}

    def _check_auth(self):

        if not self.username or not self.passkey:
            raise AuthException(('Your authentication credentials for %s are missing, check your config.') % self.name)

        return True

    def _checkAuthFromData(self, parsed_json):
        """ Check that we are authenticated. """

        if 'status' in parsed_json and 'message' in parsed_json:
            if parsed_json.get('status') == 3:
                log.warn('Invalid username or password. Check your settings')

        return True

    def search(self, search_params, age=0, ep_obj=None):
        """ Do the actual searching and JSON parsing"""

        results = []

        for mode in search_params:
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_params[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                post_data = {
                    'username': self.username,
                    'passkey': self.passkey,
                    'category': '2',  # TV Category
                    'search': search_string,
                }

                self._check_auth()
                parsed_json = self.session.get(self.urls['search'],
                                           post_data=json.dumps(post_data),
                                           returns='json')

                if not parsed_json:
                    return results

                if self._checkAuthFromData(parsed_json):
                    json_items = parsed_json.get('data', '')
                    if not json_items:
                        log.error('Resulting JSON from provider is not correct, not parsing it')

                    for item in json_items.get('torrents', []):
                        title = item.pop('name', '')
                        download_url = '{}{}'.format(
                            self.urls['download'],
                            urlencode({'id': item.pop('id', ''), 'passkey': self.passkey}))

                        if not all([title, download_url]):
                            continue

                        seeders = item.pop('seeders', 0)
                        leechers = item.pop('leechers', 0)

                        if seeders < self.minseed or leechers < self.minleech:
                            log.debug('Discarding torrent because it does not meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                            continue

                        info_hash = item.pop('info_hash', '')
                        size = item.pop('size', -1)

                        item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': info_hash}
                        if mode != 'RSS':
                            log.debug('Found result: {} with {} seeders and {} leechers'.format(
                                title, seeders, leechers))

                        items.append(item)

            results += items

        return results
