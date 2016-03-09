import logging

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class BTDiggProvider:

    def __init__(self):

        self.public = True
        self.url = 'https://btdigg.org'
        self.urls = {'api': 'https://api.btdigg.org/api/private-341ada3245790954/s02'}

        self.proper_strings = ['PROPER', 'REPACK']

        # Use this hacky way for RSS search since most results will use this codecs
        cache_params = {'RSS': ['x264', 'x264.HDTV', '720.HDTV.x264']}

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        results = []
        search_params = {'p': 0}
        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:
                search_params['q'] = search_string
                if mode != 'RSS':
                    search_params['order'] = 0
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))
                else:
                    search_params['order'] = 2

                jdata = self.get_url(self.urls['api'], params=search_params, returns='json')
                if not jdata:
                    log.debug('Provider did not return data')
                    continue

                for torrent in jdata:
                    try:
                        title = torrent.pop('name', '')
                        download_url = torrent.pop('magnet') + self._custom_trackers if torrent['magnet'] else None
                        if not all([title, download_url]):
                            continue

                        if float(torrent.pop('ff')):
                            log.debug('Ignoring result for {} since it's been reported as fake (level = {})'.format(title, torrent['ff']))
                            continue

                        if not int(torrent.pop('files')):
                            log.debug('Ignoring result for {} because it has no files'.format(title))
                            continue

                        # Provider doesn\'t provide seeders/leechers
                        seeders = 1
                        leechers = 0

                        torrent_size = torrent.pop('size')
                        size = convert_size(torrent_size) or -1

                        item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                        if mode != 'RSS':
                            log.debug('Found result: %s ' % title)

                        items.append(item)

                    except Exception:
                        continue

            results += items

        return results
