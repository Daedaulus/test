import logging

from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class XthorProvider:  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Credentials
        self.username = None
        self.password = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None
        self.freeleech = None

        # URLs
        self.url = 'https://xthor.bz'
        self.urls = {
            'login': self.url + '/takelogin.php',
            'search': self.url + '/browse.php?'
        }

        # Proper Strings
        self.proper_strings = ['PROPER']

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'submitme': 'X'
        }

        response = self.session.post(self.urls['login'], data=login_params, returns='text')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        if not re.search('donate.php', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        results = []
        if not self.login():
            return results

        """
        Séries / Pack TV 13
        Séries / TV FR 14
        Séries / HD FR 15
        Séries / TV VOSTFR 16
        Séries / HD VOSTFR 17
        Mangas (Anime) 32
        Sport 34
        """

        # Search Params
        search_params = {
            'only_free': try_int(self.freeleech),
            'searchin': 'title',
            'incldead': 0,
            'type': 'desc',
            'c13': 1, 'c14': 1, 'c15': 1,
            'c16': 1, 'c17': 1, 'c32': 1
        }

        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        def process_column_header(td):
            result = ''
            if td.a:
                result = td.a.get('title', td.a.get_text(strip=True))
            if not result:
                result = td.get_text(strip=True)
            return result

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))

            # Sorting: 1: Name, 3: Comments, 5: Size, 6: Completed, 7: Seeders, 8: Leechers (4: Time ?)
            search_params['sort'] = (7, 4)[mode == 'RSS']

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_params['search'] = search_string

                data = self.session.get(self.urls['search'], params=search_params, returns='text')
                if not data:
                    log.debug('No data returned from provider')
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('table', class_='table2 table-bordered2')
                    torrent_rows = []
                    if torrent_table:
                        torrent_rows = torrent_table.find_all('tr')

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    # Catégorie, Nom du Torrent, (Download), (Bookmark), Com., Taille, Compl�t�, Seeders, Leechers
                    labels = [process_column_header(label) for label in torrent_rows[0].find_all('td')]

                    # Skip column headers
                    for row in torrent_rows[1:]:
                        cells = row.find_all('td')
                        if len(cells) < len(labels):
                            continue

                        try:
                            title = cells[labels.index('Nom du Torrent')].get_text(strip=True)
                            download_url = self.url + '/' + row.find('a', href=re.compile('download.php'))['href']
                            if not all([title, download_url]):
                                continue

                            seeders = try_int(cells[labels.index('Seeders')].get_text(strip=True))
                            leechers = try_int(cells[labels.index('Leechers')].get_text(strip=True))

                            # Filter unseeded torrent
                            if seeders < self.minseed or leechers < self.minleech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            torrent_size = cells[labels.index('Taille')].get_text()
                            size = convert_size(torrent_size, units=units) or -1

                            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                            if mode != 'RSS':
                                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                            items.append(item)
                        except Exception:
                            continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results
