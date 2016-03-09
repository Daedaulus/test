import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class StrikeProvider(TorrentProvider):

    def __init__(self):

        TorrentProvider.__init__(self, 'Strike')

        self.public = True
        self.url = 'https://getstrike.net/'
        params = {'RSS': ['x264']}  # Use this hack for RSS search since most results will use this codec
        self.cache = tvcache.TVCache(self, min_time=10, search_params=params)
        self.minseed, self.minleech = 2 * [None]

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        results = []
        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.(u'Search Mode: {}'.format(mode), logger.DEBUG)
            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.(u'Search string: ' + search_string.strip(), logger.DEBUG)

                search_url = self.url + 'api/v2/torrents/search/?category=TV&phrase=' + search_string
                jdata = self.get_url(search_url, returns='json')
                if not jdata:
                    log.(u'No data returned from provider', logger.DEBUG)
                    return []

                results = []

                for item in jdata['torrents']:
                    seeders = ('seeds' in item and item['seeds']) or 0
                    leechers = ('leeches' in item and item['leeches']) or 0
                    title = ('torrent_title' in item and item['torrent_title']) or ''
                    torrent_size = ('size' in item and item['size'])
                    size = convert_size(torrent_size) or -1
                    download_url = ('magnet_uri' in item and item['magnet_uri']) or ''

                    if not all([title, download_url]):
                        continue

                    # Filter unseeded torrent
                    if seeders < self.minseed or leechers < self.minleech:
                        if mode != 'RSS':
                            log.(u'Discarding torrent because it doesn't meet the minimum seeders or leechers: {} (S:{} L:{})'.format
                                       (title, seeders, leechers), logger.DEBUG)
                        continue

                    if mode != 'RSS':
                        log.(u'Found result: %s with %s seeders and %s leechers' % (title, seeders, leechers), logger.DEBUG)

                    item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                    items.append(item)

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)

            results += items

        return results


provider = StrikeProvider()
