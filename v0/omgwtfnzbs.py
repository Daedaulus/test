import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class OmgwtfnzbsProvider(NZBProvider):
    def __init__(self):
        NZBProvider.__init__(self, 'OMGWTFNZBs')

        self.username = None
        self.api_key = None

        self.cache = OmgwtfnzbsCache(self)

        self.url = 'https://omgwtfnzbs.org/'
        self.urls = {
            'rss': 'https://rss.omgwtfnzbs.org/rss-download.php',
            'api': 'https://api.omgwtfnzbs.org/json/'
        }

        self.proper_strings = ['.PROPER.', '.REPACK.']

    def _check_auth(self):

        if not self.username or not self.api_key:
            log.warn('Invalid api key. Check your settings')
            return False

        return True

    def _checkAuthFromData(self, parsed_data, is_XML=True):

        if not parsed_data:
            return self._check_auth()

        if is_XML:
            # provider doesn\'t return xml on error
            return True
        else:
            if 'notice' in parsed_data:
                description_text = parsed_data.get('notice')

                if 'information is incorrect' in parsed_data.get('notice'):
                    log.warn('Invalid api key. Check your settings')

                elif '0 results matched your terms' in parsed_data.get('notice'):
                    return True

                else:
                    log.debug('Unknown error: %s' % description_text)
                    return False

            return True

    def _get_title_and_url(self, item):
        return item['release'], item['getnzb']

    def _get_size(self, item):
        return try_int(item['sizebytes'], -1)

    def search(self, search_strings, age=0, ep_obj=None):
        results = []
        if not self._check_auth():
            return results

        search_params = {
            'user': self.username,
            'api': self.api_key,
            'eng': 1,
            'catid': '19,20',  # SD,HD
            'retention': sickbeard.USENET_RETENTION,
        }

        for mode in search_strings:
            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:
                search_params['search'] = search_string
                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                data = self.get_url(self.urls['api'], params=search_params, returns='json')
                if not data:
                    log.debug('No data returned from provider')
                    continue

                if not self._checkAuthFromData(data, is_XML=False):
                    continue

                for item in data:
                    if not self._get_title_and_url(item):
                        continue

                    log.debug('Found result: {}'.format(item.get('title')))
                    items.append(item)

            results += items

        return results


class OmgwtfnzbsCache(tvcache.TVCache):
    def _get_title_and_url(self, item):
        title = item.get('title')
        if title:
            title = title.replace(' ', '.')

        url = item.get('link')
        if url:
            url = url.replace('&amp;', '&')

        return title, url

    def _getRSSData(self):
        search_params = {
            'user': provider.username,
            'api': provider.api_key,
            'eng': 1,
            'catid': '19,20'  # SD,HD
        }
        return self.getRSSFeed(self.provider.urls['rss'], params=search_params)

provider = OmgwtfnzbsProvider()
