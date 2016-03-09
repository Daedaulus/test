import logging

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class IPTorrentsProvider:  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        self.username = None
        self.password = None
        self.freeleech = False
        self.minseed = None
        self.minleech = None

        self.cache = tvcache.TVCache(self, min_time=10)  # Only poll IPTorrents every 10 minutes max

        self.urls = {'base_url': 'https://iptorrents.eu',
                     'login': 'https://iptorrents.eu/torrents/',
                     'search': 'https://iptorrents.eu/t?%s%s&q=%s&qf=#torrents'}

        self.url = self.urls['base_url']

        self.categories = '73=&60='

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for ' + self.name + ' are missing, check your config.')

        return True

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {'username': self.username,
                        'password': self.password,
                        'login': 'submit'}

        self.get_url(self.urls['login'], returns='text')
        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        # Invalid username and password combination
        if re.search('Invalid username and password combination', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        # You tried too often, please try again after 2 hours!
        if re.search('You tried too often', response):
            log.warn('You tried too often, please try again after 2 hours! Disable IPTorrents for at least 2 hours')
            return False

        return True

    def search(self, search_params, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        results = []
        if not self.login():
            return results

        freeleech = '&free=on' if self.freeleech else ''

        for mode in search_params:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_params[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                # URL with 50 tv-show results, or max 150 if adjusted in IPTorrents profile
                search_url = self.urls['search'] % (self.categories, freeleech, search_string)
                search_url += ';o=seeders' if mode != 'RSS' else ''

                data = self.get_url(search_url, returns='text')
                if not data:
                    continue

                try:
                    data = re.sub(r'(?im)<button.+?<[\/]button>', '', data, 0)
                    with BS4Parser(data, 'html5lib') as html:
                        if not html:
                            log.debug('No data returned from provider')
                            continue

                        if html.find(text='No Torrents Found!'):
                            log.debug('Data returned from provider does not contain any torrents')
                            continue

                        torrent_table = html.find('table', attrs={'class': 'torrents'})
                        torrents = torrent_table.find_all('tr') if torrent_table else []

                        # Continue only if one Release is found
                        if len(torrents) < 2:
                            log.debug('Data returned from provider does not contain any torrents')
                            continue

                        for result in torrents[1:]:
                            try:
                                title = result.find_all('td')[1].find('a').text
                                download_url = self.urls['base_url'] + result.find_all('td')[3].find('a')['href']
                                seeders = int(result.find('td', attrs={'class': 'ac t_seeders'}).text)
                                leechers = int(result.find('td', attrs={'class': 'ac t_leechers'}).text)
                                torrent_size = result.find_all('td')[5].text
                                size = convert_size(torrent_size) or -1
                            except (AttributeError, TypeError, KeyError):
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

                except Exception as e:
                    log.error('Failed parsing provider. Error: %r' % ex(e))

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)

            results += items

        return results
