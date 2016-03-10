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
log.addHandler(logging.NullHandler)


# Parse page for results
def parse(self, data, mode, torrent_method):
    torrents = data
    del torrents['total_found']

    items = []
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
                    return items
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
    return items
