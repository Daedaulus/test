class NyaaProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        TorrentProvider.__init__(self, 'NyaaTorrents')

        self.public = True
        self.supports_absolute_numbering = True
        self.anime_only = True

        self.url = 'http://www.nyaa.se'

        self.minseed = 0
        self.minleech = 0
        self.confirmed = False

        self.regex = re.compile(r'(\d+) seeder\(s\), (\d+) leecher\(s\), \d+ download\(s\) - (\d+.?\d* [KMGT]iB)(.*)', re.DOTALL)

        self.cache = tvcache.TVCache(self, min_time=20)  # only poll NyaaTorrents every 20 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        results = []
        if self.show and not self.show.is_anime:
            return results

        for mode in search_strings:
            items = []
            logger.log(u'Search Mode: {}'.format(mode), logger.DEBUG)
            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    logger.log(u'Search string: {}'.format
                               (search_string.decode('utf-8')), logger.DEBUG)

                search_params = {
                    'page': 'rss',
                    'cats': '1_0',  # All anime
                    'sort': 2,  # Sort Descending By Seeders
                    'order': 1
                }
                if mode != 'RSS':
                    search_params['term'] = search_string

                results = []
                data = self.cache.getRSSFeed(self.url, params=search_params)['entries']
                if not data:
                    logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)

                for curItem in data:
                    try:
                        title = curItem['title']
                        download_url = curItem['link']
                        if not all([title, download_url]):
                            continue

                        item_info = self.regex.search(curItem['summary'])
                        if not item_info:
                            logger.log('There was a problem parsing an item summary, skipping: {}'.format
                                       (title), logger.DEBUG)
                            continue

                        seeders, leechers, torrent_size, verified = item_info.groups()
                        seeders = try_int(seeders)
                        leechers = try_int(leechers)

                        if seeders < self.minseed or leechers < self.minleech:
                            if mode != 'RSS':
                                logger.log('Discarding torrent because it doesn\'t meet the'
                                           ' minimum seeders or leechers: {} (S:{} L:{})'.format
                                           (title, seeders, leechers), logger.DEBUG)
                            continue

                        if self.confirmed and not verified and mode != 'RSS':
                            logger.log('Found result {} but that doesn\'t seem like a verified result so I\'m ignoring it'.format
                                       (title), logger.DEBUG)
                            continue

                        size = convert_size(torrent_size) or -1
                        result = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers}
                        if mode != 'RSS':
                            logger.log('Found result: {} with {} seeders and {} leechers'.format
                                       (title, seeders, leechers), logger.DEBUG)

                        items.append(result)
                    except StandardError:
                        continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results


provider = NyaaProvider()
