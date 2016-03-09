import logging

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class BitSoupProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        TorrentProvider.__init__(self, 'BitSoup')

        self.urls = {
            'base_url': 'https://www.bitsoup.me',
            'login': 'https://www.bitsoup.me/takelogin.php',
            'detail': 'https://www.bitsoup.me/details.php?id=%s',
            'search': 'https://www.bitsoup.me/browse.php',
            'download': 'https://bitsoup.me/%s',
        }

        self.url = self.urls['base_url']

        self.username = None
        self.password = None
        self.minseed = None
        self.minleech = None

        self.cache = tvcache.TVCache(self)

        self.search_params = {
            'c42': 1, 'c45': 1, 'c49': 1, 'c7': 1
        }

    def _check_auth(self):
        if not self.username or not self.password:
            log.warn('Invalid username or password. Check your settings')

        return True

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'ssl': 'yes'
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        if re.search('Username or password incorrect', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        results = []
        if not self.login():
            return results

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                self.search_params['search'] = search_string

                data = self.get_url(self.urls['search'], params=self.search_params, returns='text')
                if not data:
                    continue

                try:
                    with BS4Parser(data, 'html.parser') as html:
                        torrent_table = html.find('table', attrs={'class': 'koptekst'})
                        torrent_rows = torrent_table.find_all('tr') if torrent_table else []

                        # Continue only if one Release is found
                        if len(torrent_rows) < 2:
                            log.debug('Data returned from provider does not contain any torrents')
                            continue

                        for result in torrent_rows[1:]:
                            cells = result.find_all('td')

                            link = cells[1].find('a')
                            download_url = self.urls['download'] % cells[2].find('a')['href']

                            try:
                                title = link.getText()
                                seeders = int(cells[10].getText().replace(',', ''))
                                leechers = int(cells[11].getText().replace(',', ''))
                                torrent_size = cells[8].getText()
                                size = convert_size(torrent_size) or -1
                            except (AttributeError, TypeError):
                                continue

                            if not all([title, download_url]):
                                continue

                                # Filter unseeded torrent
                            if seeders < self.minseed or leechers < self.minleech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            if seeders >= 32768 or leechers >= 32768:
                                continue

                            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                            if mode != 'RSS':
                                log.debug('Found result: %s with %s seeders and %s leechers' % (title, seeders, leechers))

                            items.append(item)

                except Exception:
                    log.warn('Failed parsing provider. Traceback: %s' % traceback.format_exc())

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)

            results += items

        return results


provider = BitSoupProvider()
