import logging
import re

from requests import Session
from requests.compat import urljoin
# from requests.utils import dict_from_cookiejar
#
# from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler)


class BinSearchProvider:

    def __init__(self):

        self.session = Session()

        self.url = 'https://www.binsearch.info'
        self.urls = {'rss': urljoin(self.url, 'rss.php')}

        self.public = True
        self.supports_backlog = False

        self.cache = BinSearchCache(min_time=30)  # only poll Binsearch every 30 minutes max


class BinSearchCache:
    def __init__(self, **kwargs):
        kwargs.pop('search_params', None)  # does not use _getRSSData so strip param from kwargs...

        # compile and save our regular expressions

        # this pulls the title from the URL in the description
        self.descTitleStart = re.compile(r'^.*https?://www\.binsearch\.info/.b=')
        self.descTitleEnd = re.compile('&amp;.*$')

        # these clean up the horrible mess of a title if the above fail
        self.titleCleaners = [
            re.compile(r'.?yEnc.?\(\d+/\d+\)$'),
            re.compile(r' \[\d+/\d+\] '),
        ]

    def _get_title_and_url(self, item):
        title = item.get('description')
        if title:
            if self.descTitleStart.match(title):
                title = self.descTitleStart.sub('', title)
                title = self.descTitleEnd.sub('', title)
                title = title.replace('+', '.')
            else:
                # just use the entire title, looks hard/impossible to parse
                title = item.get('title')
                if title:
                    for titleCleaner in self.titleCleaners:
                        title = titleCleaner.sub('', title)

        url = item.get('link')
        if url:
            url = url.replace('&amp;', '&')

        return title, url

    def update_cache(self):
        # check if we should update
        if not self.shouldUpdate():
            return

        # clear cache
        self._clearCache()

        # set updated
        self.setLastUpdate()

        cl = []
        for group in ['alt.binaries.hdtv', 'alt.binaries.hdtv.x264', 'alt.binaries.tv', 'alt.binaries.tvseries', 'alt.binaries.teevee']:
            search_params = {'max': 50, 'g': group}
            data = self.getRSSFeed(self.urls['rss'], search_params)['entries']
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

    @staticmethod
    def _check_auth(data):
        return data if data['feed'] and data['feed']['title'] != 'Invalid Link' else None
