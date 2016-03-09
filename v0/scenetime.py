import logging

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class SceneTimeProvider:  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        self.username = None
        self.password = None
        self.minseed = None
        self.minleech = None

        self.cache = tvcache.TVCache(self)  # only poll SceneTime every 20 minutes max

        self.urls = {'base_url': 'https://www.scenetime.com',
                     'login': 'https://www.scenetime.com/takelogin.php',
                     'detail': 'https://www.scenetime.com/details.php?id=%s',
                     'search': 'https://www.scenetime.com/browse.php?search=%s%s',
                     'download': 'https://www.scenetime.com/download.php/%s/%s'}

        self.url = self.urls['base_url']

        self.categories = '&c2=1&c43=13&c9=1&c63=1&c77=1&c79=1&c100=1&c101=1'

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {'username': self.username,
                        'password': self.password}

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        if re.search('Username or password incorrect', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    def search(self, search_params, age=0, ep_obj=None):  # pylint: disable=too-many-branches, too-many-locals
        results = []
        if not self.login():
            return results

        for mode in search_params:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_params[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_url = self.urls['search'] % (quote(search_string), self.categories)

                data = self.get_url(search_url, returns='text')
                if not data:
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('div', id='torrenttable')
                    torrent_rows = []
                    if torrent_table:
                        torrent_rows = torrent_table.select('tr')

                    # Continue only if one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    # Scenetime apparently uses different number of cells in #torrenttable based
                    # on who you are. This works around that by extracting labels from the first
                    # <tr> and using their index to find the correct download/seeders/leechers td.
                    labels = [label.get_text(strip=True) for label in torrent_rows[0].find_all('td')]

                    for result in torrent_rows[1:]:
                        try:
                            cells = result.find_all('td')

                            link = cells[labels.index('Name')].find('a')
                            torrent_id = link['href'].replace('details.php?id=', '').split('&')[0]

                            title = link.get_text(strip=True)
                            download_url = self.urls['download'] % (torrent_id, '%s.torrent' % title.replace(' ', '.'))

                            seeders = try_int(cells[labels.index('Seeders')].get_text(strip=True))
                            leechers = try_int(cells[labels.index('Leechers')].get_text(strip=True))
                            torrent_size = cells[labels.index('Size')].get_text()

                            size = convert_size(torrent_size) or -1

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
