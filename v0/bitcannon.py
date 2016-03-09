import logging

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class BitCannonProvider:

    def __init__(self):

        self.session = Session()

        self.minseed = None
        self.minleech = None
        self.custom_url = None
        self.api_key = None

    def search(self, search_strings, age=0, ep_obj=None):
        results = []

        url = 'http://localhost:3000/'
        if self.custom_url:
            if not validators.url(self.custom_url):
                log.warn('Invalid custom url set, please check your settings')
                return results
            url = self.custom_url

        search_params = {}

        anime = ep_obj and ep_obj.show and ep_obj.show.anime
        search_params['category'] = ('tv', 'anime')[bool(anime)]

        if self.api_key:
            search_params['apiKey'] = self.api_key

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:
                search_params['q'] = search_string
                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string))

                search_url = urljoin(url, 'api/search')
                parsed_json = self.session.get(search_url, params=search_params, returns='json')
                if not parsed_json:
                    log.debug('No data returned from provider')
                    continue

                if not self._check_auth_from_data(parsed_json):
                    return results

                for result in parsed_json.pop('torrents', {}):
                    try:
                        title = result.pop('title', '')

                        info_hash = result.pop('infoHash', '')
                        download_url = 'magnet:?xt=urn:btih:' + info_hash
                        if not all([title, download_url, info_hash]):
                            continue

                        swarm = result.pop('swarm', None)
                        if swarm:
                            seeders = try_int(swarm.pop('seeders', 0))
                            leechers = try_int(swarm.pop('leechers', 0))
                        else:
                            seeders = leechers = 0

                        if seeders < self.minseed or leechers < self.minleech:
                            if mode != 'RSS':
                                log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                            continue

                        size = convert_size(result.pop('size', -1)) or -1
                        item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                        if mode != 'RSS':
                            log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                        items.append(item)
                    except (AttributeError, TypeError, KeyError, ValueError):
                        continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results

    @staticmethod
    def _check_auth_from_data(data):
        if not all([isinstance(data, dict),
                    data.pop('status', 200) != 401,
                    data.pop('message', '') != 'Invalid API key']):

            log.warn('Invalid api key. Check your settings')
            return False

        return True

