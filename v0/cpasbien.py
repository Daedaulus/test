import logging
import re

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class CpasbienProvider:

    def __init__(self):

        self.session = Session()

        self.public = True
        self.minseed = None
        self.minleech = None
        self.url = 'http://www.cpasbien.io'

        self.proper_strings = ['PROPER', 'REPACK']

    def search(self, search_strings, age=0, ep_obj=None):
        results = []
        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))
                    search_url = self.url + '/recherche/' + search_string.replace('.', '-').replace(' ', '-') + '.html,trie-seeds-d'
                else:
                    search_url = self.url + '/view_cat.php?categorie=series&trie=date-d'

                data = self.session.get(search_url, returns='text')
                if not data:
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_rows = html(class_=re.compile('ligne[01]'))
                    for result in torrent_rows:
                        try:
                            title = result.find(class_='titre').get_text(strip=True).replace('HDTV', 'HDTV x264-CPasBien')
                            title = re.sub(r' Saison', ' Season', title, flags=re.IGNORECASE)
                            tmp = result.find('a')['href'].split('/')[-1].replace('.html', '.torrent').strip()
                            download_url = (self.url + '/telechargement/%s' % tmp)
                            if not all([title, download_url]):
                                continue

                            seeders = result.find(class_='up').get_text(strip=True)
                            leechers = result.find(class_='down').get_text(strip=True)
                            if seeders < self.minseed or leechers < self.minleech:
                                if mode != 'RSS':
                                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                                continue

                            torrent_size = result.find(class_='poid').get_text(strip=True)

                            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                            if mode != 'RSS':
                                log.debug('Found result: %s with %s seeders and %s leechers' % (title, seeders, leechers))

                            items.append(item)
                        except Exception:
                            continue

            results += items

        return results
