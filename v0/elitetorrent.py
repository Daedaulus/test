import logging

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class elitetorrentProvider:

    def __init__(self):

        self.session = Session()

        self.onlyspasearch = None
        self.minseed = None
        self.minleech = None

        self.urls = {
            'base_url': 'http://www.elitetorrent.net',
            'search': 'http://www.elitetorrent.net/torrents.php'
        }

        self.url = self.urls['base_url']

    def search(self, search_strings, age=0, ep_obj=None):
        results = []
        lang_info = '' if not ep_obj or not ep_obj.show else ep_obj.show.lang

        """
        Search query:
        http://www.elitetorrent.net/torrents.php?cat=4&modo=listado&orden=fecha&pag=1&buscar=fringe

        cat = 4 => Shows
        modo = listado => display results mode
        orden = fecha => order
        buscar => Search show
        pag = 1 => page number
        """

        search_params = {
            'cat': 4,
            'modo': 'listado',
            'orden': 'fecha',
            'pag': 1,
            'buscar': ''

        }

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))

            # Only search if user conditions are true
            if self.onlyspasearch and lang_info != 'es' and mode != 'RSS':
                log.debug('Show info is not spanish, skipping provider search')
                continue

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                search_string = re.sub(r'S0*(\d*)E(\d*)', r'\1x\2', search_string)
                search_params['buscar'] = search_string.strip() if mode != 'RSS' else ''

                data = self.session.get(self.urls['search'], params=search_params, returns='text')
                if not data:
                    continue

                try:
                    with BS4Parser(data, 'html5lib') as html:
                        torrent_table = html.find('table', class_='fichas-listado')
                        torrent_rows = torrent_table.find_ll('tr') if torrent_table else []

                        if len(torrent_rows) < 2:
                            log.debug('Data returned from provider does not contain any torrents')
                            continue

                        for row in torrent_rows[1:]:
                            try:
                                download_url = self.urls['base_url'] + row.find('a')['href']
                                title = self._processTitle(row.find('a', class_='nombre')['title'])
                                seeders = row.find('td', class_='semillas').get_text(strip=True)
                                leechers = row.find('td', class_='clientes').get_text(strip=True)

                                # Provider does not provide size
                                size = -1

                            except (AttributeError, TypeError, KeyError, ValueError):
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
                    log.warn('Failed parsing provider. Traceback: %s' % traceback.format_exc())

            results += items

        return results

    @staticmethod
    def _processTitle(title):

        # Quality, if no literal is defined it's HDTV
        if 'calidad' not in title:
            title += ' HDTV x264'

        title = title.replace('(calidad baja)', 'HDTV x264')
        title = title.replace('(Buena calidad)', '720p HDTV x264')
        title = title.replace('(Alta calidad)', '720p HDTV x264')
        title = title.replace('(calidad regular)', 'DVDrip x264')
        title = title.replace('(calidad media)', 'DVDrip x264')

        # Language, all results from this provider have spanish audio, we append it to title (avoid to download undesired torrents)
        title += ' SPANISH AUDIO'
        title += '-ELITETORRENT'

        return title.strip()
