import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class NorbitsProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """Main provider object"""

    def __init__(self):
        """ Initialize the class """
        TorrentProvider.__init__(self, 'Norbits')

        self.username = None
        self.passkey = None
        self.minseed = None
        self.minleech = None

        self.cache = tvcache.TVCache(self, min_time=20)  # only poll Norbits every 15 minutes max

        self.url = 'https://norbits.net'
        self.urls = {'search': self.url + '/api2.php?action=torrents',
                     'download': self.url + '/download.php?'}

    def _check_auth(self):

        if not self.username or not self.passkey:
            raise AuthException(('Your authentication credentials for %s are '
                                 'missing, check your config.') % self.name)

        return True

    def _checkAuthFromData(self, parsed_json):  # pylint: disable=invalid-name
        """ Check that we are authenticated. """

        if 'status' in parsed_json and 'message' in parsed_json:
            if parsed_json.get('status') == 3:
                log.warn('Invalid username or password. Check your settings')

        return True

    def search(self, search_params, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        """ Do the actual searching and JSON parsing"""

        results = []

        for mode in search_params:
            items = []
            log.('Search Mode: {}'.format(mode), logger.DEBUG)

            for search_string in search_params[mode]:
                if mode != 'RSS':
                    log.('Search string: {}'.format
                               (search_string.decode('utf-8')), logger.DEBUG)

                post_data = {
                    'username': self.username,
                    'passkey': self.passkey,
                    'category': '2',  # TV Category
                    'search': search_string,
                }

                self._check_auth()
                parsed_json = self.get_url(self.urls['search'],
                                           post_data=json.dumps(post_data),
                                           returns='json')

                if not parsed_json:
                    return results

                if self._checkAuthFromData(parsed_json):
                    json_items = parsed_json.get('data', '')
                    if not json_items:
                        log.('Resulting JSON from provider is not correct, '
                                   'not parsing it', logger.ERROR)

                    for item in json_items.get('torrents', []):
                        title = item.pop('name', '')
                        download_url = '{}{}'.format(
                            self.urls['download'],
                            urlencode({'id': item.pop('id', ''), 'passkey': self.passkey}))

                        if not all([title, download_url]):
                            continue

                        seeders = try_int(item.pop('seeders', 0))
                        leechers = try_int(item.pop('leechers', 0))

                        if seeders < self.minseed or leechers < self.minleech:
                            log.('Discarding torrent because it does not meet '
                                       'the minimum seeders or leechers: {} (S:{} L:{})'.format
                                       (title, seeders, leechers), logger.DEBUG)
                            continue

                        info_hash = item.pop('info_hash', '')
                        size = convert_size(item.pop('size', -1), -1)

                        item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': info_hash}
                        if mode != 'RSS':
                            log.('Found result: {} with {} seeders and {} leechers'.format(
                                title, seeders, leechers), logger.DEBUG)

                        items.append(item)
            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)

            results += items

        return results


provider = NorbitsProvider()  # pylint: disable=invalid-name
