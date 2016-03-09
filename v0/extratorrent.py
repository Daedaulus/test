import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class ExtraTorrentProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        TorrentProvider.__init__(self, 'ExtraTorrent')

        self.urls = {
            'index': 'http://extratorrent.cc',
            'rss': 'http://extratorrent.cc/rss.xml',
        }

        self.url = self.urls['index']

        self.public = True
        self.minseed = None
        self.minleech = None
        self.custom_url = None

        self.cache = tvcache.TVCache(self, min_time=30)  # Only poll ExtraTorrent every 30 minutes max
        self.headers.update({'User-Agent': USER_AGENT})
        self.search_params = {'cid': 8}

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        results = []
        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                self.search_params.update({'type': ('search', 'rss')[mode == 'RSS'], 'search': search_string})
                search_url = self.urls['rss'] if not self.custom_url else self.urls['rss'].replace(self.urls['index'], self.custom_url)

                data = self.get_url(search_url, params=self.search_params, returns='text')
                if not data:
                    log.debug('No data returned from provider')
                    continue

                if not data.startswith('<?xml'):
                    log.info('Expected xml but got something else, is your mirror failing?')
                    continue

                with BS4Parser(data, 'html5lib') as parser:
                    for item in parser.findAll('item'):
                        try:
                            title = re.sub(r'^<!\[CDATA\[|\]\]>$', '', item.find('title').get_text(strip=True))
                            seeders = try_int(item.find('seeders').get_text(strip=True))
                            leechers = try_int(item.find('leechers').get_text(strip=True))
                            torrent_size = item.find('size').get_text()
                            size = convert_size(torrent_size) or -1

                            if sickbeard.TORRENT_METHOD == 'blackhole':
                                enclosure = item.find('enclosure')  # Backlog doesnt have enclosure
                                download_url = enclosure['url'] if enclosure else item.find('link').next.strip()
                                download_url = re.sub(r'(.*)/torrent/(.*).html', r'\1/download/\2.torrent', download_url)
                            else:
                                info_hash = item.find('info_hash').get_text(strip=True)
                                download_url = 'magnet:?xt=urn:btih:' + info_hash + '&dn=' + title + self._custom_trackers

                        except (AttributeError, TypeError, KeyError, ValueError):
                            continue

                        if not all([title, download_url]):
                            continue

                            # Filter unseeded torrent
                        if seeders < self.minseed or leechers < self.minleech:
                            if mode != 'RSS':
                                log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                            continue

                        item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                        if mode != 'RSS':
                            log.debug('Found result: %s with %s seeders and %s leechers' % (title, seeders, leechers))

                        items.append(item)

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results


provider = ExtraTorrentProvider()
