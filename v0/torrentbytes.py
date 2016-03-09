import logging

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class TorrentBytesProvider:  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Credentials
        self.username = None
        self.password = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None
        self.freeleech = False

        # URLs
        self.url = 'https://www.torrentbytes.net'
        self.urls = {
            'login': urljoin(self.url, 'takelogin.php'),
            'search': urljoin(self.url, 'browse.php')
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {'username': self.username,
                        'password': self.password,
                        'login': 'Log in!'}

        response = self.session.post(self.urls['login'], data=login_params, returns='text')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        if re.search('Username or password incorrect', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        results = []
        if not self.login():
            return results

        search_params = {
            'c41': 1, 'c33': 1, 'c38': 1, 'c32': 1, 'c37': 1
        }

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_params['search'] = search_string
                data = self.session.get(self.urls['search'], params=search_params, returns='text')
                if not data:
                    log.debug('No data returned from provider')
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('table', border='1')
                    torrent_rows = torrent_table.find_all('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        log.debug('Data returned from provider does not contain any torrents')
                        continue

                    # 'Type', 'Name', Files', 'Comm.', 'Added', 'TTL', 'Size', 'Snatched', 'Seeders', 'Leechers'
                    labels = [label.get_text(strip=True) for label in torrent_rows[0].find_all('td')]

                    for result in torrent_rows[1:]:
                        try:
                            cells = result.find_all('td')

                            download_url = urljoin(self.url, cells[labels.index('Name')].find('a', href=re.compile(r'download.php\?id='))['href'])
                            title_element = cells[labels.index('Name')].find('a', href=re.compile(r'details.php\?id='))
                            title = title_element.get('title', '') or title_element.get_text(strip=True)
                            if not all([title, download_url]):
                                continue

                            if self.freeleech:
                                # Free leech torrents are marked with green [F L] in the title (i.e. <font color=green>[F&nbsp;L]</font>)
                                freeleech = cells[labels.index('Name')].find('font', color='green')
                                if not freeleech or freeleech.get_text(strip=True) != '[F\xa0L]':
                                    continue

                            seeders = try_int(cells[labels.index('Seeders')].get_text(strip=True))
                            leechers = try_int(cells[labels.index('Leechers')].get_text(strip=True))

                            # Filter unseeded torrent
                            if seeders < self.minseed or leechers < self.minleech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            # Need size for failed downloads handling
                            torrent_size = cells[labels.index('Size')].get_text(strip=True)
                            size = convert_size(torrent_size) or -1
                            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}

                            if mode != 'RSS':
                                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                            items.append(item)
                        except (AttributeError, TypeError):
                            continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results
