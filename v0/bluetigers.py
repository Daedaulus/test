import logging
import re

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class BlueTigersProvider:

    def __init__(self):

        self.session = Session()

        # Credentials
        self.username = None
        self.password = None
        self.token = None

        self.urls = {
            'base_url': 'https://www.bluetigers.ca/',
            'search': 'https://www.bluetigers.ca/torrents-search.php',
            'login': 'https://www.bluetigers.ca/account-login.php',
            'download': 'https://www.bluetigers.ca/torrents-details.php?id=%s&hit=1',
        }

        self.search_params = {
            'c16': 1, 'c10': 1, 'c130': 1, 'c131': 1, 'c17': 1, 'c18': 1, 'c19': 1, 'c9': 1
        }

        self.url = self.urls['base_url']

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'take_login': '1'
        }

        response = self.session.post(self.urls['login'], data=login_params, returns='text')

        if not response:
            check_login = self.session.get(self.urls['base_url'], returns='text')
            if re.search('account-logout.php', check_login):
                return True
            else:
                log.warn('Unable to connect to provider')
                return False

        if re.search('account-login.php', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):
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

                data = self.session.get(self.urls['search'], params=self.search_params, returns='text')
                if not data:
                    continue

                try:
                    with BS4Parser(data, 'html5lib') as html:
                        result_linkz = html.findAll('a', href=re.compile('torrents-details'))

                        if not result_linkz:
                            log.debug('Data returned from provider do not contains any torrent')
                            continue

                        if result_linkz:
                            for link in result_linkz:
                                title = link.text
                                download_url = self.urls['base_url'] + link['href']
                                download_url = download_url.replace('torrents-details', 'download')
                                # FIXME
                                torrent_size = -1
                                seeders = 1
                                leechers = 0

                                if not title or not download_url:
                                    continue

                                # # Filter unseeded torrent
                                # if seeders < self.minseed or leechers < self.minleech:
                                #    if mode != 'RSS':
                                #        log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                #    continue

                                item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                                if mode != 'RSS':
                                    log.debug('Found result: %s ' % title)

                                items.append(item)

                except Exception:
                    log.error('Failed parsing provider. Traceback: %s' % traceback.format_exc())

            results += items

        return results
