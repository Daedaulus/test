import logging

from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class HoundDawgsProvider:  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        self.username = None
        self.password = None
        self.minseed = None
        self.minleech = None
        self.freeleech = None
        self.ranked = None

        self.urls = {
            'base_url': 'https://hounddawgs.org/',
            'search': 'https://hounddawgs.org/torrents.php',
            'login': 'https://hounddawgs.org/login.php'
        }

        self.url = self.urls['base_url']

        self.search_params = {
            'filter_cat[85]': 1,
            'filter_cat[58]': 1,
            'filter_cat[57]': 1,
            'filter_cat[74]': 1,
            'filter_cat[92]': 1,
            'filter_cat[93]': 1,
            'order_by': 's3',
            'order_way': 'desc',
            'type': '',
            'userid': '',
            'searchstr': '',
            'searchimdb': '',
            'searchtags': ''
        }

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'keeplogged': 'on',
            'login': 'Login'
        }

        self.session.get(self.urls['base_url'], returns='text')
        response = self.session.post(self.urls['login'], data=login_params, returns='text')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        if re.search('Dit brugernavn eller kodeord er forkert.', response) \
                or re.search('<title>Login :: HoundDawgs</title>', response) \
                or re.search('Dine cookies er ikke aktiveret.', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        results = []
        if not self.login():
            return results

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                self.search_params['searchstr'] = search_string

                data = self.session.get(self.urls['search'], params=self.search_params, returns='text')
                if not data:
                    log.debug('URL did not return data')
                    continue

                strTableStart = '<table class=\'torrent_table'
                startTableIndex = data.find(strTableStart)
                trimmedData = data[startTableIndex:]
                if not trimmedData:
                    continue

                try:
                    with BS4Parser(trimmedData, 'html5lib') as html:
                        result_table = html.find('table', {'id': 'torrent_table'})

                        if not result_table:
                            log.debug('Data returned from provider does not contain any torrents')
                            continue

                        result_tbody = result_table.find('tbody')
                        entries = result_tbody.contents
                        del entries[1::2]

                        for result in entries[1:]:

                            torrent = result.find_all('td')
                            if len(torrent) <= 1:
                                break

                            allAs = (torrent[1]).find_all('a')

                            try:
                                notinternal = result.find('img', src='/static//common/user_upload.png')
                                if self.ranked and notinternal:
                                    log.debug('Found a user uploaded release, Ignoring it..')
                                    continue
                                freeleech = result.find('img', src='/static//common/browse/freeleech.png')
                                if self.freeleech and not freeleech:
                                    continue
                                title = allAs[2].string
                                download_url = self.urls['base_url'] + allAs[0].attrs['href']
                                torrent_size = result.find('td', class_='nobr').find_next_sibling('td').string
                                if torrent_size:
                                    size = convert_size(torrent_size) or -1
                                seeders = try_int((result.findAll('td')[6]).text)
                                leechers = try_int((result.findAll('td')[7]).text)

                            except (AttributeError, TypeError):
                                continue

                            if not title or not download_url:
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

                except Exception:
                    log.error('Failed parsing provider. Traceback: %s' % traceback.format_exc())

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)

            results += items

        return results
