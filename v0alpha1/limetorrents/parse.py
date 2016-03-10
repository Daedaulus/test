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
    with BS4Parser(data, 'html5lib') as document:
        if not document.is_xml:
            log.info('Expected xml but got something else, is your mirror failing?')
            return items

        entries = document.findAll('item')
        if not entries:
            log.info('Returned xml contained no results')
            return items

        for item in entries:
            title = item.title.text
            # Use the itorrents link limetorrents provides,
            # unless it is not itorrents or we are not using blackhole
            # because we want to use magnets if connecting direct to client
            # so that proxies work.
            download_url = item.enclosure['url']
            if torrent_method != 'blackhole' or 'itorrents' not in download_url:
                download_url = item.enclosure['url']
                # http://itorrents.org/torrent/C7203982B6F000393B1CE3A013504E5F87A46A7F.torrent?title=The-Night-of-the-Generals-(1967)[BRRip-1080p-x264-by-alE13-DTS-AC3][Lektor-i-Napisy-PL-Eng][Eng]
                # Keep the hash a separate string for when its needed for failed
                torrent_hash = re.match(r'(.*)([A-F0-9]{40})(.*)', download_url, re.IGNORECASE).group(2)
                download_url = 'magnet:?xt=urn:btih:' + torrent_hash + '&dn=' + title + self._custom_trackers

            if not (title and download_url):
                continue
            # seeders and leechers are presented diferently when doing a search and when looking for newly added
            if mode == 'RSS':
                # <![CDATA[
                # Category: <a href='http://www.limetorrents.cc/browse-torrents/TV-shows/'>TV shows</a><br /> Seeds: 1<br />Leechers: 0<br />Size: 7.71 GB<br /><br /><a href='http://www.limetorrents.cc/Owen-Hart-of-Gold-Djon91-torrent-7180661.html'>More @ limetorrents.cc</a><br />
                # ]]>
                description = item.find('description')
                seeders = description('br')[0].next_sibling.strip().lstrip('Seeds: ')
                leechers = description('br')[1].next_sibling.strip().lstrip('Leechers: ')
            else:
                # <description>Seeds: 6982 , Leechers 734</description>
                description = item.find('description').text.partition(',')
                seeders = description[0].lstrip('Seeds: ').strip()
                leechers = description[2].lstrip('Leechers ').strip()

            torrent_size = item.find('size').text

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
