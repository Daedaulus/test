import logging

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class RarbgProvider:  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        self.public = True
        self.minseed = None
        self.ranked = None
        self.sorting = None
        self.minleech = None
        self.token = None
        self.token_expires = None

        # Spec: https://torrentapi.org/apidocs_v2.txt
        self.url = 'https://rarbg.com'
        self.urls = {'api': 'http://torrentapi.org/pubapi_v2.php'}

        self.proper_strings = ['{{PROPER|REPACK}}']

    def login(self):
        if self.token and self.token_expires and datetime.datetime.now() < self.token_expires:
            return True

        login_params = {
            'get_token': 'get_token',
            'format': 'json',
            'app_id': 'sickrage2'
        }

        response = self.session.get(self.urls['api'], params=login_params, returns='json')
        if not response:
            log.warn('Unable to connect to provider')
            return False

        self.token = response.get('token', None)
        self.token_expires = datetime.datetime.now() + datetime.timedelta(minutes=14) if self.token else None
        return self.token is not None

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        results = []
        if not self.login():
            return results

        search_params = {
            'app_id': 'sickrage2',
            'category': 'tv',
            'min_seeders': try_int(self.minseed),
            'min_leechers': try_int(self.minleech),
            'limit': 100,
            'format': 'json_extended',
            'ranked': try_int(self.ranked),
            'token': self.token,
        }

        if ep_obj is not None:
            ep_indexerid = ep_obj.show.indexerid
            ep_indexer = ep_obj.show.indexer
        else:
            ep_indexerid = None
            ep_indexer = None

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            if mode == 'RSS':
                search_params['sort'] = 'last'
                search_params['mode'] = 'list'
                search_params.pop('search_string', None)
                search_params.pop('search_tvdb', None)
            else:
                search_params['sort'] = self.sorting if self.sorting else 'seeders'
                search_params['mode'] = 'search'

                if ep_indexer == INDEXER_TVDB and ep_indexerid:
                    search_params['search_tvdb'] = ep_indexerid
                else:
                    search_params.pop('search_tvdb', None)

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    search_params['search_string'] = search_string
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                time.sleep(cpu_presets[sickbeard.CPU_PRESET])
                data = self.session.get(self.urls['api'], params=search_params, returns='json')
                if not isinstance(data, dict):
                    log.debug('No data returned from provider')
                    continue

                error = data.get('error')
                error_code = data.get('error_code')
                # Don't log when {'error':'No results found','error_code':20}
                # List of errors: https://github.com/rarbg/torrentapi/issues/1#issuecomment-114763312
                if error:
                    if try_int(error_code) != 20:
                        log.info(error)
                    continue

                torrent_results = data.get('torrent_results')
                if not torrent_results:
                    log.debug('Data returned from provider does not contain any torrents')
                    continue

                for item in torrent_results:
                    try:
                        title = item.pop('title')
                        download_url = item.pop('download')
                        if not all([title, download_url]):
                            continue

                        seeders = item.pop('seeders')
                        leechers = item.pop('leechers')
                        if seeders < self.minseed or leechers < self.minleech:
                            if mode != 'RSS':
                                log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                            continue

                        torrent_size = item.pop('size', -1)
                        size = convert_size(torrent_size) or -1

                        if mode != 'RSS':
                            log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

                        result = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers}
                        items.append(result)
                    except Exception:
                        continue

            # For each search mode sort all the items by seeders
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results
