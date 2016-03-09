import logging

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class FreshOnTVProvider:  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        self.session = Session()

        self._uid = None
        self._hash = None
        self.username = None
        self.password = None
        self.minseed = None
        self.minleech = None
        self.freeleech = False

        self.urls = {'base_url': 'https://freshon.tv/',
                     'login': 'https://freshon.tv/login.php?action=makelogin',
                     'detail': 'https://freshon.tv/details.php?id=%s',
                     'search': 'https://freshon.tv/browse.php?incldead=%s&words=0&cat=0&search=%s',
                     'download': 'https://freshon.tv/download.php?id=%s&type=torrent'}

        self.url = self.urls['base_url']

        self.cookies = None

    def _check_auth(self):

        if not self.username or not self.password:
            log.warn('Invalid username or password. Check your settings')

        return True

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        if self._uid and self._hash:
            add_dict_to_cookiejar(self.session.cookies, self.cookies)
        else:
            login_params = {'username': self.username,
                            'password': self.password,
                            'login': 'submit'}

            response = self.session.post(self.urls['login'], data=login_params, returns='text')
            if not response:
                log.warn('Unable to connect to provider')
                return False

            if re.search('/logout.php', response):

                try:
                    if dict_from_cookiejar(self.session.cookies)['uid'] and dict_from_cookiejar(self.session.cookies)['pass']:
                        self._uid = dict_from_cookiejar(self.session.cookies)['uid']
                        self._hash = dict_from_cookiejar(self.session.cookies)['pass']

                        self.cookies = {'uid': self._uid,
                                        'pass': self._hash}
                        return True
                except Exception:
                    log.warn('Unable to login to provider (cookie)')
                    return False

            else:
                if re.search('Username does not exist in the userbase or the account is not confirmed yet.', response):
                    log.warn('Invalid username or password. Check your settings')

                if re.search('DDoS protection by CloudFlare', response):
                    log.warn('Unable to login to provider due to CloudFlare DDoS javascript check')

                    return False

    def search(self, search_params, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        results = []
        if not self.login():
            return results

        freeleech = '3' if self.freeleech else '0'

        for mode in search_params:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_params[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_url = self.urls['search'] % (freeleech, search_string)
                init_html = self.session.get(search_url, returns='text')
                max_page_number = 0

                if not init_html:
                    log.debug('No data returned from provider')
                    continue

                try:
                    with BS4Parser(init_html, 'html5lib') as init_soup:

                        # Check to see if there is more than 1 page of results
                        pager = init_soup.find('div', {'class': 'pager'})
                        if pager:
                            page_links = pager.find_all('a', href=True)
                        else:
                            page_links = []

                        if len(page_links) > 0:
                            for lnk in page_links:
                                link_text = lnk.text.strip()
                                if link_text.isdigit():
                                    page_int = int(link_text)
                                    if page_int > max_page_number:
                                        max_page_number = page_int

                        # limit page number to 15 just in case something goes wrong
                        if max_page_number > 15:
                            max_page_number = 15
                        # limit RSS search
                        if max_page_number > 3 and mode == 'RSS':
                            max_page_number = 3
                except Exception:
                    log.error('Failed parsing provider. Traceback: %s' % traceback.format_exc())
                    continue

                data_response_list = [init_html]

                # Freshon starts counting pages from zero, even though it displays numbers from 1
                if max_page_number > 1:
                    for i in range(1, max_page_number):

                        time.sleep(1)
                        page_search_url = search_url + '&page=' + str(i)
                        # log.debug('Search string: ' + page_search_url)
                        page_html = self.session.get(page_search_url, returns='text')

                        if not page_html:
                            continue

                        data_response_list.append(page_html)

                try:

                    for data_response in data_response_list:

                        with BS4Parser(data_response, 'html5lib') as html:

                            torrent_rows = html.findAll('tr', {'class': re.compile('torrent_[0-9]*')})

                            # Continue only if a Release is found
                            if len(torrent_rows) == 0:
                                log.debug('Data returned from provider does not contain any torrents')
                                continue

                            for individual_torrent in torrent_rows:

                                # skip if torrent has been nuked due to poor quality
                                if individual_torrent.find('img', alt='Nuked') is not None:
                                    continue

                                try:
                                    title = individual_torrent.find('a', {'class': 'torrent_name_link'})['title']
                                except Exception:
                                    log.warn('Unable to parse torrent title. Traceback: %s ' % traceback.format_exc())
                                    continue

                                try:
                                    details_url = individual_torrent.find('a', {'class': 'torrent_name_link'})['href']
                                    torrent_id = int((re.match('.*?([0-9]+)$', details_url).group(1)).strip())
                                    download_url = self.urls['download'] % (str(torrent_id))
                                    seeders = try_int(individual_torrent.find('td', {'class': 'table_seeders'}).find('span').text.strip(), 1)
                                    leechers = try_int(individual_torrent.find('td', {'class': 'table_leechers'}).find('a').text.strip(), 0)
                                    torrent_size = individual_torrent.find('td', {'class': 'table_size'}).get_text()
                                    size = convert_size(torrent_size) or -1
                                except Exception:
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

                except Exception:
                    log.error('Failed parsing provider. Traceback: %s' % traceback.format_exc())

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results
