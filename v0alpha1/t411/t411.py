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
log.addHandler(logging.NullHandler())


# Search page
def search(
    provider,
    search_url,
    search_strings,
    search_params,
    torrent_method=None,
    ep_obj=None,
    *args, **kwargs
):
    # TODO: Enable Custom URL Support

    searches = []
    # Authenticate
    with suppress(NotImplementedError, AttributeError):
        if not provider.login(provider.login_params):
            return searches

    for mode in search_params:
        items = []
        logger.log(u"Search Mode: {}".format(mode), logger.DEBUG)
        for search_string in search_params[mode]:

            if mode != 'RSS':
                logger.log(u"Search string: {}".format(search_string.decode("utf-8")),
                           logger.DEBUG)

            search_urlS = ([self.urls['search'] % (search_string, u) for u in self.subcategories], [self.urls['rss']])[mode == 'RSS']
            for search_url in search_urlS:
                data = self.get_url(search_url, returns='json')
                if not data:
                    continue

            # Append search result
            searches.append(data)
    return searches
