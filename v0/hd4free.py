import logging
import re

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class HD4FreeProvider:

    def __init__(self):

        self.session = Session()

        self.url = 'https://hd4free.xyz'
        self.urls = {'search': urljoin(self.url, '/searchapi.php')}

        self.freeleech = None
        self.username = None
        self.api_key = None
        self.minseed = None
        self.minleech = None

    def _check_auth(self):
        if self.username and self.api_key:
            return True

        log.warn('Your authentication credentials for %s are missing, check your config.' % self.name)
        return False

    def search(self, search_strings, age=0, ep_obj=None):
        results = []
        if not self._check_auth:
            return results

        search_params = {
            'tv': 'true',
            'username': self.username,
            'apikey': self.api_key
        }

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:
                if self.freeleech:
                    search_params['fl'] = 'true'
                else:
                    search_params.pop('fl', '')

                if mode != 'RSS':
                    log.debug('Search string: ' + search_string.strip())
                    search_params['search'] = search_string
                else:
                    search_params.pop('search', '')

                jdata = self.session.get(self.urls['search'], params=search_params, returns='json')
                if not jdata:
                    log.debug('No data returned from provider')
                    continue

                try:
                    if jdata['0']['total_results'] == 0:
                        log.debug('Provider has no results for this search')
                        continue
                except Exception:
                    continue

                for i in jdata:
                    try:
                        title = jdata[i]['release_name']
                        download_url = jdata[i]['download_url']
                        if not all([title, download_url]):
                            continue

                        seeders = jdata[i]['seeders']
                        leechers = jdata[i]['leechers']
                        if seeders < self.minseed or leechers < self.minleech:
                            if mode != 'RSS':
                                log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                            continue

                        torrent_size = str(jdata[i]['size']) + ' MB'
                        item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}

                        if mode != 'RSS':
                            log.debug('Found result: %s with %s seeders and %s leechers' % (title, seeders, leechers))

                        items.append(item)
                    except Exception:
                        continue

            results += items

        return results
