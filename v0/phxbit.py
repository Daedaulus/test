import logging

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class PhxBitProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'PhxBit')

        # Credentials
        self.username = None
        self.password = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # URLs
        self.url = 'https://phxbit.com'
        self.urls = {
            'login': urljoin(self.url, '/connect.php'),
            'search': urljoin(self.url, '/sphinx.php')
        }

        # Proper Strings
        self.proper_strings = ['PROPER']

        # Cache
        self.cache = tvcache.TVCache(self, min_time=30)

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        if not re.search('dons.php', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {
            'order': 'desc',
            'sort': 'normal',
            'group': 'series'
        }

        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        def process_column_header(td):
            result = ''
            if td.img:
                result = td.img.get('alt', '')
            if not result:
                result = td.get_text(strip=True)
            return result

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    # Use exact=1 parameter if we're doing a backlog or manual search
                    search_params['exact'] = 1
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_params['q'] = search_string

                data = self.get_url(self.urls['search'], params=search_params, returns='text')
                if not data:
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('table')
                    torrent_rows = torrent_table.find_all('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    # Catégorie, Nom,  DL, Com, Taille, C, Seed, Leech,	Share
                    labels = [process_column_header(label) for label in torrent_rows[0].find_all('td')]

                    # Skip column headers
                    for result in torrent_rows[1:]:
                        cells = result.find_all('td')
                        if len(cells) < len(labels):
                            continue

                        try:
                            title = cells[labels.index('Nom')].get_text(strip=True)
                            download_url = cells[labels.index('DL')].find('a')['href']
                            if not all([title, download_url]):
                                continue

                            seeders = try_int(cells[labels.index('Seed')].get_text(strip=True))
                            leechers = try_int(cells[labels.index('Leech')].get_text(strip=True))

                            # Filter unseeded torrent
                            if seeders < self.minseed or leechers < self.minleech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            torrent_size = cells[labels.index('Taille')].get_text(strip=True)
                            size = convert_size(torrent_size, units=units) or -1

                            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                            if mode != 'RSS':
                                log.debug('Found result: %s with %s seeders and %s leechers' % (title, seeders, leechers))

                            items.append(item)
                        except StandardError:
                            continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results


provider = PhxBitProvider()
