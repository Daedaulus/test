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
log.addHandler(logging.NullHandler)


# Parse page for results
def parse(self, data, mode, torrent_method):
    items = []
    with BS4Parser(data, 'html5lib') as html:
        torrent_table = html.find('table', attrs={'class': 'copyright'})
        torrent_rows = torrent_table('tr') if torrent_table else []

        # Continue only if at least one Release is found
        if len(torrent_rows) < 3:
            log.debug('Data returned from provider does not contain any torrents')
            last_page = 1
            return items

        if len(torrent_rows) < 42:
            last_page = 1

        # Skip column headers
        for result in torrent_table('tr')[2:]:

            try:
                link = result.find('td').find('a')
                title = link.string
                download_url = self.urls['download'] % result('td')[8].find('a')['href'][-8:]
                leechers = result('td')[3]('td')[1].text
                leechers = int(leechers.strip('[]'))
                seeders = result('td')[3]('td')[2].text
                seeders = int(seeders.strip('[]'))
                torrent_size = result('td')[3]('td')[3].text.strip('[]') + ' GB'
            except (AttributeError, TypeError):
                continue

            filename_qt = self._reverse_quality(self._episode_quality(result))
            for text in self.hdtext:
                title1 = title
                title = title.replace(text, filename_qt)
                if title != title1:
                    break

            if Quality.nameQuality(title) == Quality.UNKNOWN:
                title += filename_qt

            if not self._is_italian(result) and not self.subtitle:
                log.debug('Torrent is subtitled, skipping: %s ' % title)
                continue

            if self.engrelease and not self._is_english(result):
                log.debug('Torrent isnt english audio/subtitled , skipping: %s ' % title)
                continue

            search_show = re.split(r'([Ss][\d{1,2}]+)', search_string)[0]
            show_title = search_show
            rindex = re.search(r'([Ss][\d{1,2}]+)', title)
            if rindex:
                show_title = title[:rindex.start()]
                ep_params = title[rindex.start():]
            if show_title.lower() != search_show.lower() and search_show.lower() in show_title.lower():
                new_title = search_show + ep_params
                title = new_title

            if not all([title, download_url]):
                continue

            if self._is_season_pack(title):
                title = re.sub(r'([Ee][\d{1,2}\-?]+)', '', title)

            # Filter unseeded torrent
            if seeders < self.min_seed or leechers < self.min_leech:
                if mode != 'RSS':
                    log.debug('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {} (S:{} L:{})'.format(title, seeders, leechers))
                continue

            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
            if mode != 'RSS':
                log.debug('Found result: {} with {} seeders and {} leechers'.format(title, seeders, leechers))

            items.append(item)

    return items
