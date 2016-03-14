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


# Parse page for results
def parse(self, data, mode, torrent_method):
    items = []

    error = data.get('error')
    error_code = data.get('error_code')
    # Don't log when {'error':'No results found','error_code':20}
    # List of errors: https://github.com/rarbg/torrentapi/issues/1#issuecomment-114763312
    if error:
        if error_code != 20:
            log.info(error)
        return items

    torrent_results = data.get('torrent_results')
    if not torrent_results:
        log.debug('Data returned from provider does not contain any torrents')
        return items

    for item in torrent_results:
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

    return items
