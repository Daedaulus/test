import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class SCCProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        TorrentProvider.__init__(self, 'SceneAccess')

        self.username = None
        self.password = None
        self.minseed = None
        self.minleech = None

        self.cache = tvcache.TVCache(self)  # only poll SCC every 20 minutes max

        self.urls = {
            'base_url': 'https://sceneaccess.eu',
            'login': 'https://sceneaccess.eu/login',
            'detail': 'https://www.sceneaccess.eu/details?id=%s',
            'search': 'https://sceneaccess.eu/all?search=%s&method=1&%s',
            'download': 'https://www.sceneaccess.eu/%s'
        }

        self.url = self.urls['base_url']

        self.categories = {
            'Season': 'c26=26&c44=44&c45=45',  # Archive, non-scene HD, non-scene SD; need to include non-scene because WEB-DL packs get added to those categories
            'Episode': 'c17=17&c27=27&c33=33&c34=34&c44=44&c45=45',  # TV HD, TV SD, non-scene HD, non-scene SD, foreign XviD, foreign x264
            'RSS': 'c17=17&c26=26&c27=27&c33=33&c34=34&c44=44&c45=45'  # Season + Episode
        }

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'submit': 'come on in'
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        if re.search(r'Username or password incorrect', response) \
                or re.search(r'<title>SceneAccess \| Login</title>', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    @staticmethod
    def _isSection(section, text):
        title = r'<title>.+? \| %s</title>' % section
        return re.search(title, text, re.IGNORECASE)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals,too-many-branches, too-many-statements
        results = []
        if not self.login():
            return results

        for mode in search_strings:
            items = []
            if mode != 'RSS':
                log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_url = self.urls['search'] % (quote(search_string), self.categories[mode])

                try:
                    data = self.get_url(search_url, returns='text')
                    time.sleep(cpu_presets[sickbeard.CPU_PRESET])
                except Exception as e:
                    log.warn('Unable to fetch data. Error: %s' % repr(e))

                if not data:
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('table', attrs={'id': 'torrents-table'})
                    torrent_rows = torrent_table.find_all('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    for result in torrent_table.find_all('tr')[1:]:

                        try:
                            link = result.find('td', attrs={'class': 'ttr_name'}).find('a')
                            url = result.find('td', attrs={'class': 'td_dl'}).find('a')

                            title = link.string
                            if re.search(r'\.\.\.', title):
                                data = self.get_url(urljoin(self.url, link['href']), returns='text')
                                if data:
                                    with BS4Parser(data) as details_html:
                                        title = re.search('(?<=').+(?<!')', details_html.title.string).group(0)
                            download_url = self.urls['download'] % url['href']
                            seeders = int(result.find('td', attrs={'class': 'ttr_seeders'}).string)
                            leechers = int(result.find('td', attrs={'class': 'ttr_leechers'}).string)
                            torrent_size = result.find('td', attrs={'class': 'ttr_size'}).contents[0]

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

                        item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                        if mode != 'RSS':
                            log.debug('Found result: %s with %s seeders and %s leechers' % (title, seeders, leechers))

                        items.append(item)

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)

            results += items

        return results


provider = SCCProvider()
