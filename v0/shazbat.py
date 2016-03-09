import logging

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class ShazbatProvider(TorrentProvider):

    def __init__(self):

        TorrentProvider.__init__(self, 'Shazbat.tv')

        self.supports_backlog = False

        self.passkey = None
        self.options = None

        self.cache = ShazbatCache(self, min_time=20)

        self.url = 'http://www.shazbat.tv'
        self.urls = {
            'login': urljoin(self.url, 'login'),
            'rss_recent': urljoin(self.url, 'rss/recent'),
            # 'rss_queue': urljoin(self.url, 'rss/download_queue'),
            # 'rss_followed': urljoin(self.url, 'rss/followed')
        }

    def _check_auth(self):
        if not self.passkey:
            raise AuthException('Your authentication credentials are missing, check your config.')

        return True

    def _checkAuthFromData(self, data):
        if not self.passkey:
            self._check_auth()
        elif not (data['entries'] and data['feed']):
            log.warn('Invalid username or password. Check your settings')

        return True


class ShazbatCache(tvcache.TVCache):
    def _getRSSData(self):
        params = {
            'passkey': self.provider.passkey,
            'fname': 'true',
            'limit': 100,
            'duration': '2 hours'
        }

        return self.getRSSFeed(self.provider.urls['rss_recent'], params=params)

    def _checkAuth(self, data):
        return self.provider._checkAuthFromData(data)  # pylint: disable=protected-access

provider = ShazbatProvider()
