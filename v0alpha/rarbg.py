from datetime import datetime, timedelta
import logging
import re
from time import sleep
import traceback

import validators
from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class RarbgProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'https://rarbg.com'  # Spec: https://torrentapi.org/apidocs_v2.txt
        self.urls = {
            'base': self.url,
            'api': 'http://torrentapi.org/pubapi_v2.php'
        }

        # Credentials
        self.public = True
        self.token = None
        self.token_expires = None
        self.login_params = {
            'get_token': 'get_token',
            'format': 'json',
            'app_id': 'medusa'
        }

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None

        # Search Params
        self.ranked = None
        self.sorting = None
        self.search_params = {
            'app_id': 'sickrage2',
            'category': 'tv',
            'min_seeders': self.min_seed,
            'min_leechers': self.min_leech,
            'limit': 100,
            'format': 'json_extended',
            'ranked': self.ranked,
            'token': self.token,
        }

        # Categories

        # Proper Strings
        self.proper_strings = [
            '{{PROPER|REPACK}}',
        ]

        # Options

    # Search page
    def search(
        self,
        search_strings,
        search_params,
        torrent_method=None,
        ep_obj=None,
        *args, **kwargs
    ):
        results = []

        if not self.login():
            return results

        if ep_obj is not None:
            ep_indexerid = ep_obj.show.indexerid
            ep_indexer = ep_obj.show.indexer
        else:
            ep_indexerid = None
            ep_indexer = None

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))
            if mode == 'RSS':
                search_params['sort'] = 'last'
                search_params['mode'] = 'list'
                search_params.pop('search_string', None)
                search_params.pop('search_tvdb', None)
            else:
                search_params['sort'] = self.sorting if self.sorting else 'seeders'
                search_params['mode'] = 'search'

                if ep_indexer == INDEXER_TVDB and ep_indexerid:
                    search_params['search_tvdb'] = ep_indexerid
                else:
                    search_params.pop('search_tvdb', None)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    search_params['search_string'] = search_string
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                sleep(cpu_presets[sickbeard.CPU_PRESET])
                data = self.session.get(self.urls['api'], params=search_params).json()
                if not isinstance(data, dict):
                    log.debug('No data returned from provider')
                    continue

                error = data.get('error')
                error_code = data.get('error_code')
                # Don't log when {'error':'No results found','error_code':20}
                # List of errors: https://github.com/rarbg/torrentapi/issues/1#issuecomment-114763312
                if error:
                    if error_code != 20:
                        log.info(error)
                    continue

                torrent_results = data.get('torrent_results')
                if not torrent_results:
                    log.debug('Data returned from provider does not contain any torrents')
                    continue

                for item in torrent_results:
                    try:
                        title = item.pop('title')
                        download_url = item.pop('download')
                        if not all([title, download_url]):
                            continue

                        seeders = item.pop('seeders')
                        leechers = item.pop('leechers')

                        # Filter unseeded torrent
                        if seeders < self.min_seed or leechers < self.min_leech:
                            if mode != 'RSS':
                                log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                            continue

                        torrent_size = item.pop('size', -1)

                        result = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers}

                        if mode != 'RSS':
                            log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                        items.append(result)

                    except Exception:
                        continue

            results += items

        return results

    # Parse page for results
    def parse(self):
        raise NotImplementedError

    # Log in
    def login(self, login_params):
        if self.token and self.token_expires and datetime.now() < self.token_expires:
            return True

        response = self.session.get(self.urls['api'], params=login_params).json()
        if not response:
            log.warn('Unable to connect to provider')
            return False

        self.token = response.get('token', None)
        self.token_expires = datetime.now() + timedelta(minutes=14) if self.token else None

        return self.token is not None

    # Validate login
    def check_auth(self):
        raise NotImplementedError
