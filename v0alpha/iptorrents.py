from datetime import datetime, timedelta
import logging
import re
from time import sleep
import traceback

import validators
from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class IPTorrentsProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'https://iptorrents.eu/'
        self.urls = {
            'base': self.url,
            'login': urljoin(self.url, 'torrents/'),
            'search': urljoin(self.url, 't?%s%s&q=%s&qf=#torrents'),
        }

        # Credentials
        self.username = None
        self.password = None
        self.login_params = {
            'username': self.username,
            'password': self.password,
            'login': 'submit',
        }

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None
        self.freeleech = False

        # Proper Strings

        # Search Params

        # Categories
        self.categories = '73=&60='

        # Proper Strings

        # Options

    # Search page
    def search(
        self,
        search_strings,
        search_params,
        torrent_method=None,
        ep_obj=None,
        *args, **kwargs
    ):
        results = []

        if not self.login():
            return results

        freeleech = '&free=on' if self.freeleech else ''

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_url = self.urls['search'] % (self.categories, freeleech, search_string)
                search_url += ';o=seeders' if mode != 'RSS' else ''
                data = self.session.get(search_url).text
                if not data:
                    log.debug('No data returned from provider')
                    continue

                try:
                    data = re.sub(r'(?im)<button.+?<[/]button>', '', data, 0)
                    with BS4Parser(data, 'html5lib') as html:
                        if not html:
                            log.debug('No data returned from provider')
                            continue

                        if html.find(text='No Torrents Found!'):
                            log.debug('Data returned from provider does not contain any torrents')
                            continue

                        torrent_table = html.find('table', attrs={'class': 'torrents'})
                        torrents = torrent_table('tr') if torrent_table else []

                        # Continue only if one Release is found
                        if len(torrents) < 2:
                            log.debug('Data returned from provider does not contain any torrents')
                            continue

                        for result in torrents[1:]:
                            try:
                                title = result('td')[1].find('a').text
                                download_url = self.urls['base'] + result('td')[3].find('a')['href']
                                seeders = int(result.find('td', attrs={'class': 'ac t_seeders'}).text)
                                leechers = int(result.find('td', attrs={'class': 'ac t_leechers'}).text)
                                torrent_size = result('td')[5].text
                            except (AttributeError, TypeError, KeyError):
                                continue

                            if not all([title, download_url]):
                                continue

                            # Filter unseeded torrent
                            if seeders < self.min_seed or leechers < self.min_leech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}

                            if mode != 'RSS':
                                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                            items.append(item)

                except Exception as e:
                    log.error('Failed parsing provider. Error: %r' % ex(e))

            results += items

        return results

    # Parse page for results
    def parse(self):
        raise NotImplementedError

    # Log in
    def login(self, login_params):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        _ = self.session.get(self.urls['login'])  # Using get first for cookies?
        response = self.session.post(self.urls['login'], data=login_params).text
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

    # Validate login
    def check_auth(self):
        if not self.username or not self.password:
            raise Exception('Your authentication credentials for ' + self.name + ' are missing, check your config.')
        return True
