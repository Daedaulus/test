import logging

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class TransmitTheNetProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'TransmitTheNet')

        # Credentials
        self.username = None
        self.password = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None
        self.freeleech = None

        # URLs
        self.url = 'https://transmithe.net/'
        self.urls = {
            'login': urljoin(self.url, '/login.php'),
            'search': urljoin(self.url, '/torrents.php'),
        }

        # Proper Strings

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
            'keeplogged': 'on',
            'login': 'Login'
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        if re.search('Username Incorrect', response) or re.search('Password Incorrect', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        results = []
        if not self.login():
            return results

        for mode in search_strings:
            items = []
            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_params = {
                    'searchtext': search_string,
                    'filter_freeleech': (0, 1)[self.freeleech is True],
                    'order_by': ('seeders', 'time')[mode == 'RSS'],
                    'order_way': 'desc'
                }

                if not search_string:
                    del search_params['searchtext']

                data = self.get_url(self.urls['search'], params=search_params, returns='text')
                if not data:
                    log.debug('No data returned from provider')
                    continue

                try:
                    with BS4Parser(data, 'html5lib') as html:
                        torrent_table = html.find('table', {'id': 'torrent_table'})
                        if not torrent_table:
                            log.debug('Data returned from %s does not contain any torrents' % self.name)
                            continue

                        torrent_rows = torrent_table.findAll('tr', {'class': 'torrent'})

                        # Continue only if one Release is found
                        if not torrent_rows:
                            log.debug('Data returned from %s does not contain any torrents' % self.name)
                            continue

                        for torrent_row in torrent_rows:
                            freeleech = torrent_row.find('img', alt='Freeleech') is not None
                            if self.freeleech and not freeleech:
                                continue

                            download_item = torrent_row.find('a', {'title': 'Download Torrent'})
                            if not download_item:
                                continue

                            download_url = urljoin(self.urls, download_item['href'])

                            temp_anchor = torrent_row.find('a', {'data-src': True})
                            title = temp_anchor['data-src'].rsplit('.', 1)[0]
                            if not title:
                                title = torrent_row.find('a', onmouseout='return nd();').string
                                title = title.replace('[', '').replace(']', '').replace('/ ', '') if title else ''

                            temp_anchor = torrent_row.find('span', class_='time').parent.find_next_sibling()
                            if not all([title, download_url]):
                                continue

                            seeders = try_int(temp_anchor.text.strip())
                            leechers = try_int(temp_anchor.find_next_sibling().text.strip())

                            # Filter unseeded torrent
                            if seeders < self.minseed or leechers < self.minleech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            cells = torrent_row.find_all('td')
                            torrent_size = cells[5].text.strip()
                            size = convert_size(torrent_size) or -1

                            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                            if mode != 'RSS':
                                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                            items.append(item)
                except Exception:
                    log.error('Failed parsing provider. Traceback: %s' % traceback.format_exc())

            # For each search mode sort all the items by seeders
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results


provider = TransmitTheNetProvider()
