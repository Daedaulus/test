import logging

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class ShazbatProvider:

    def __init__(self):

        self.session = Session()

        self.supports_backlog = False

        # Credentials
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
            'passkey': self.passkey,
            'fname': 'true',
            'limit': 100,
            'duration': '2 hours'
        }

        return self.getRSSFeed(self.urls['rss_recent'], params=params)

    def _checkAuth(self, data):
        return self._checkAuthFromData(data)
