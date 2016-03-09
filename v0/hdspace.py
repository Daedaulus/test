import logging

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class HDSpaceProvider:  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        self.username = None
        self.password = None
        self.minseed = None
        self.minleech = None

        self.urls = {'base_url': 'https://hd-space.org/',
                     'login': 'https://hd-space.org/index.php?page=login',
                     'search': 'https://hd-space.org/index.php?page=torrents&search=%s&active=1&options=0',
                     'rss': 'https://hd-space.org/rss_torrents.php?feed=dl'}

        self.categories = [15, 21, 22, 24, 25, 40]  # HDTV/DOC 1080/720, bluray, remux
        self.urls['search'] += '&category='
        for cat in self.categories:
            self.urls['search'] += str(cat) + '%%3B'
            self.urls['rss'] += '&cat[]=' + str(cat)
        self.urls['search'] = self.urls['search'][:-4]  # remove extra %%3B

        self.url = self.urls['base_url']

    def _check_auth(self):

        if not self.username or not self.password:
            log.warn('Invalid username or password. Check your settings')

        return True

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        if 'pass' in dict_from_cookiejar(self.session.cookies):
            return True

        login_params = {'uid': self.username,
                        'pwd': self.password}

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        if re.search('Password Incorrect', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        results = []
        if not self.login():
            return results

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    search_url = self.urls['search'] % (quote_plus(search_string.replace('.', ' ')),)
                else:
                    search_url = self.urls['search'] % ''

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                data = self.get_url(search_url, returns='text')
                if not data or 'please try later' in data:
                    log.debug('No data returned from provider')
                    continue

                # Search result page contains some invalid html that prevents html parser from returning all data.
                # We cut everything before the table that contains the data we are interested in thus eliminating
                # the invalid html portions
                try:
                    data = data.split('<div id='information'></div>')[1]
                    index = data.index('<table')
                except ValueError:
                    log.error('Could not find main torrent table')
                    continue

                html = BeautifulSoup(data[index:], 'html5lib')
                if not html:
                    log.debug('No html data parsed from provider')
                    continue

                torrents = html.findAll('tr')
                if not torrents:
                    continue

                # Skip column headers
                for result in torrents[1:]:
                    if len(result.contents) < 10:
                        # skip extraneous rows at the end
                        continue

                    try:
                        dl_href = result.find('a', attrs={'href': re.compile(r'download.php.*')})['href']
                        title = re.search('f=(.*).torrent', dl_href).group(1).replace('+', '.')
                        download_url = self.urls['base_url'] + dl_href
                        seeders = int(result.find('span', attrs={'class': 'seedy'}).find('a').text)
                        leechers = int(result.find('span', attrs={'class': 'leechy'}).find('a').text)
                        torrent_size = re.match(r'.*?([0-9]+,?\.?[0-9]* [KkMmGg]+[Bb]+).*', str(result), re.DOTALL).group(1)
                        size = convert_size(torrent_size) or -1

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

                    except (AttributeError, TypeError, KeyError, ValueError):
                        continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results
