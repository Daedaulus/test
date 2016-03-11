from datetime import datetime, timedelta
import logging
# import re
from time import sleep
import traceback

import validators
from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class TorrentProjectProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'https://torrentproject.se/'
        self.urls = {
            'base': self.url,
        }
        self.custom_url = None

        # Credentials
        self.public = True

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None

        # Search Params
        self.search_params = {
            'out': 'json',
            'filter': 2101,
            'num': 150
        }

        # Categories

        # Proper Strings

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

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_params['s'] = search_string

                if self.custom_url:
                    if not validators.url(self.custom_url):
                        log.warn('Invalid custom url set, please check your settings')
                        return results
                    search_url = self.custom_url
                else:
                    search_url = self.url

                torrents = self.session.get(search_url, params=search_params).json()
                if not (torrents and 'total_found' in torrents and int(torrents['total_found']) > 0):
                    log.debug('Data returned from provider does not contain any torrents')
                    continue

                del torrents['total_found']

                results = []
                for i in torrents:
                    title = torrents[i]['title']
                    seeders = torrents[i]['seeds']
                    leechers = torrents[i]['leechs']
                    if seeders < self.min_seed or leechers < self.min_leech:
                        if mode != 'RSS':
                            log.debug('Torrent doesn\'t meet minimum seeds & leechers not selecting : %s' % title)
                        continue

                    t_hash = torrents[i]['torrent_hash']
                    torrent_size = torrents[i]['torrent_size']

                    try:
                        assert seeders < 10
                        assert mode != 'RSS'
                        log.debug('Torrent has less than 10 seeds getting dyn trackers: ' + title)

                        if self.custom_url:
                            if not validators.url(self.custom_url):
                                log.warn('Invalid custom url set, please check your settings')
                                return results
                            trackers_url = self.custom_url
                        else:
                            trackers_url = self.url

                        trackers_url = urljoin(trackers_url, t_hash)
                        trackers_url = urljoin(trackers_url, '/trackers_json')
                        jdata = self.session.get(trackers_url).json()

                        assert jdata != 'maintenance'
                        download_url = 'magnet:?xt=urn:btih:' + t_hash + '&dn=' + title + ''.join(['&tr=' + s for s in jdata])
                    except (Exception, AssertionError):
                        download_url = 'magnet:?xt=urn:btih:' + t_hash + '&dn=' + title + self._custom_trackers

                    if not all([title, download_url]):
                        continue

                    item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': t_hash}

                    if mode != 'RSS':
                        log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                    items.append(item)

            results += items

        return results

    # Parse page for results
    def parse(self):
        raise NotImplementedError

    # Log in
    def login(self, login_params):
        raise NotImplementedError

    # Validate login
    def check_auth(self):
        raise NotImplementedError
