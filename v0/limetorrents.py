import logging

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class LimeTorrentsProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        TorrentProvider.__init__(self, 'LimeTorrents')

        self.urls = {
            'index': 'https://www.limetorrents.cc/',
            'search': 'https://www.limetorrents.cc/searchrss/20/',
            'rss': 'https://www.limetorrents.cc/rss/20/'
        }

        self.url = self.urls['index']

        self.public = True
        self.minseed = None
        self.minleech = None
        self.headers.update({'User-Agent': USER_AGENT})
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        self.cache = tvcache.TVCache(self, search_params={'RSS': ['rss']})

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-branches,too-many-locals
        results = []
        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                try:
                    search_url = (self.urls['rss'], self.urls['search'] + search_string)[mode != 'RSS']

                    data = self.get_url(search_url, returns='text')
                    if not data:
                        log.debug('No data returned from provider')
                        continue

                    if not data.startswith('<?xml'):
                        log.info('Expected xml but got something else, is your mirror failing?')
                        continue

                    data = BeautifulSoup(data, 'html5lib')

                    entries = data.findAll('item')
                    if not entries:
                        log.info('Returned xml contained no results')
                        continue

                    for item in entries:
                        try:
                            title = item.title.text
                            # Use the itorrents link limetorrents provides,
                            # unless it is not itorrents or we are not using blackhole
                            # because we want to use magnets if connecting direct to client
                            # so that proxies work.
                            download_url = item.enclosure['url']
                            if sickbeard.TORRENT_METHOD != 'blackhole' or 'itorrents' not in download_url:
                                download_url = item.enclosure['url']
                                # http://itorrents.org/torrent/C7203982B6F000393B1CE3A013504E5F87A46A7F.torrent?title=The-Night-of-the-Generals-(1967)[BRRip-1080p-x264-by-alE13-DTS-AC3][Lektor-i-Napisy-PL-Eng][Eng]
                                # Keep the hash a separate string for when its needed for failed
                                torrent_hash = re.match(r'(.*)([A-F0-9]{40})(.*)', download_url, re.IGNORECASE).group(2)
                                download_url = 'magnet:?xt=urn:btih:' + torrent_hash + '&dn=' + title + self._custom_trackers

                            if not (title and download_url):
                                continue
                            # seeders and leechers are presented diferently when doing a search and when looking for newly added
                            if mode == 'RSS':
                                # <![CDATA[
                                # Category: <a href='http://www.limetorrents.cc/browse-torrents/TV-shows/'>TV shows</a><br /> Seeds: 1<br />Leechers: 0<br />Size: 7.71 GB<br /><br /><a href='http://www.limetorrents.cc/Owen-Hart-of-Gold-Djon91-torrent-7180661.html'>More @ limetorrents.cc</a><br />
                                # ]]>
                                description = item.find('description')
                                seeders = try_int(description.find_all('br')[0].next_sibling.strip().lstrip('Seeds: '))
                                leechers = try_int(description.find_all('br')[1].next_sibling.strip().lstrip('Leechers: '))
                            else:
                                # <description>Seeds: 6982 , Leechers 734</description>
                                description = item.find('description').text.partition(',')
                                seeders = try_int(description[0].lstrip('Seeds: ').strip())
                                leechers = try_int(description[2].lstrip('Leechers ').strip())

                            torrent_size = item.find('size').text

                            size = convert_size(torrent_size) or -1

                        except (AttributeError, TypeError, KeyError, ValueError):
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

                except (AttributeError, TypeError, KeyError, ValueError):
                    log.error('Failed parsing provider. Traceback: %r' % traceback.format_exc())

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)

            results += items

        return results


provider = LimeTorrentsProvider()
