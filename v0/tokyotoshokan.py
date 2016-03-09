import logging

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class TokyoToshokanProvider:  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        self.public = True
        self.supports_absolute_numbering = True
        self.anime_only = True

        self.minseed = None
        self.minleech = None

        self.url = 'http://tokyotosho.info/'
        self.urls = {
            'search': self.url + 'search.php',
            'rss': self.url + 'rss.php'
        }

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        results = []
        if not self.show or not self.show.is_anime:
            return results

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_params = {
                    'terms': search_string,
                    'type': 1,  # get anime types
                }

                data = self.get_url(self.urls['search'], params=search_params, returns='text')
                if not data:
                    continue

                with BS4Parser(data, 'html5lib') as soup:
                    torrent_table = soup.find('table', class_='listing')
                    torrent_rows = torrent_table.find_all('tr') if torrent_table else []

                    # Continue only if one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    a = 1 if len(torrent_rows[0].find_all('td')) < 2 else 0

                    for top, bot in zip(torrent_rows[a::2], torrent_rows[a + 1::2]):
                        try:
                            desc_top = top.find('td', class_='desc-top')
                            title = desc_top.get_text(strip=True)
                            download_url = desc_top.find('a')['href']

                            desc_bottom = bot.find('td', class_='desc-bot').get_text(strip=True)
                            size = convert_size(desc_bottom.split('|')[1].strip('Size: ')) or -1

                            stats = bot.find('td', class_='stats').get_text(strip=True)
                            sl = re.match(r'S:(?P<seeders>\d+)L:(?P<leechers>\d+)C:(?:\d+)ID:(?:\d+)', stats.replace(' ', ''))
                            seeders = try_int(sl.group('seeders')) if sl else 0
                            leechers = try_int(sl.group('leechers')) if sl else 0
                        except Exception:
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
