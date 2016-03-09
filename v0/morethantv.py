import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class MoreThanTVProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'MoreThanTV')

        # Credentials
        self.username = None
        self.password = None
        self._uid = None
        self._hash = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None
        self.freeleech = None

        # URLs
        self.url = 'https://www.morethan.tv/'
        self.urls = {
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'torrents.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Cache
        self.cache = tvcache.TVCache(self)

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for ' + self.name + ' are missing, check your config.')

        return True

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'keeplogged': '1',
            'login': 'Log in',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            log.warn(u'Unable to connect to provider')
            return False

        if re.search('Your username or password was incorrect.', response):
            log.warn(u'Invalid username or password. Check your settings')
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {
            'tags_type': 1,
            'order_by': 'time',
            'order_way': 'desc',
            'action': 'basic',
            'searchsubmit': 1,
            'searchstr': ''
        }

        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        def process_column_header(td):
            result = ''
            if td.a and td.a.img:
                result = td.a.img.get('title', td.a.get_text(strip=True))
            if not result:
                result = td.get_text(strip=True)
            return result

        for mode in search_strings:
            items = []
            log.(u'Search Mode: {}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.(u'Search string: {}'.format(search_string.decode('utf-8')),
                               logger.DEBUG)

                search_params['searchstr'] = search_string

                data = self.get_url(self.urls['search'], params=search_params, returns='text')
                if not data:
                    log.(u'No data returned from provider', logger.DEBUG)
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('table', class_='torrent_table')
                    torrent_rows = torrent_table.find_all('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.(u'Data returned from provider does not contain any torrents', logger.DEBUG)
                        continue

                    labels = [process_column_header(label) for label in torrent_rows[0].find_all('td')]

                    # Skip column headers
                    for result in torrent_rows[1:]:
                        try:
                            # skip if torrent has been nuked due to poor quality
                            if result.find('img', alt='Nuked'):
                                continue

                            title = result.find('a', title='View torrent').get_text(strip=True)
                            download_url = urljoin(self.url, result.find('span', title='Download').parent['href'])
                            if not all([title, download_url]):
                                continue

                            cells = result.find_all('td')
                            seeders = try_int(cells[labels.index('Seeders')].get_text(strip=True))
                            leechers = try_int(cells[labels.index('Leechers')].get_text(strip=True))

                            # Filter unseeded torrent
                            if seeders < self.minseed or leechers < self.minleech:
                                if mode != 'RSS':
                                    log.(u'Discarding torrent because it doesn't meet the'
                                               u' minimum seeders or leechers: {} (S:{} L:{})'.format
                                               (title, seeders, leechers), logger.DEBUG)
                                continue

                            torrent_size = cells[labels.index('Size')].get_text(strip=True)
                            size = convert_size(torrent_size, units=units) or -1

                            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                            if mode != 'RSS':
                                log.(u'Found result: {} with {} seeders and {} leechers'.format
                                           (title, seeders, leechers), logger.DEBUG)

                            items.append(item)
                        except StandardError:
                            continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results


provider = MoreThanTVProvider()
