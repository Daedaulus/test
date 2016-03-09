import logging

from requests.compat import urljoin

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class WombleProvider:

    def __init__(self):

        self.public = True

        self.url = 'http://newshost.co.za'
        self.urls = {'rss': urljoin(self.url, 'rss')}
        self.supports_backlog = False

        self.cache = WombleCache(self, min_time=20)


class WombleCache(tvcache.TVCache):
    def updateCache(self):

        if not self.shouldUpdate():
            return

        self._clearCache()
        self.setLastUpdate()

        cl = []
        search_params_list = [{'sec': 'tv-x264'}, {'sec': 'tv-hd'}, {'sec': 'tv-sd'}, {'sec': 'tv-dvd'}]
        for search_params in search_params_list:
            search_params.update({'fr': 'false'})
            data = self.getRSSFeed(self.provider.urls['rss'], params=search_params)['entries']
            if not data:
                log.debug('No data returned from provider')
                continue

            for item in data:
                ci = self._parseItem(item)
                if ci:
                    cl.append(ci)

        if len(cl) > 0:
            cache_db_con = self._getDB()
            cache_db_con.mass_action(cl)

    def _checkAuth(self, data):
        return data if data['feed'] and data['feed']['title'] != 'Invalid Link' else None
