import logging

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class TorrentzProvider:  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        self.session = Session()

        # Credentials
        self.public = True
        self.confirmed = True

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # URLs
        self.url = 'https://torrentz.eu/'
        self.urls = {
            'verified': 'https://torrentz.eu/feed_verified',
            'feed': 'https://torrentz.eu/feed',
            'base': self.url,
        }
        self.headers.update({'User-Agent': USER_AGENT})

    @staticmethod
    def _split_description(description):
        match = re.findall(r'[0-9]+', description)
        return int(match[0]) * 1024 ** 2, int(match[1]), int(match[2])

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        results = []

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:
                search_url = self.urls['verified'] if self.confirmed else self.urls['feed']
                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                data = self.session.get(search_url, params={'q': search_string}, returns='text')
                if not data:
                    log.debug('No data returned from provider')
                    continue

                if not data.startswith('<?xml'):
                    log.info('Expected xml but got something else, is your mirror failing?')
                    continue

                try:
                    with BS4Parser(data, 'html5lib') as parser:
                        for item in parser.findAll('item'):
                            if item.category and 'tv' not in item.category.get_text(strip=True):
                                continue

                            title = item.title.text.rsplit(' ', 1)[0].replace(' ', '.')
                            t_hash = item.guid.text.rsplit('/', 1)[-1]

                            if not all([title, t_hash]):
                                continue

                            download_url = 'magnet:?xt=urn:btih:' + t_hash + '&dn=' + title + self._custom_trackers
                            torrent_size, seeders, leechers = self._split_description(item.find('description').text)
                            size = convert_size(torrent_size) or -1

                            # Filter unseeded torrent
                            if seeders < self.minseed or leechers < self.minleech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            result = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': t_hash}
                            items.append(result)
                except Exception:
                    log.error('Failed parsing provider. Traceback: %r' % traceback.format_exc())

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results
