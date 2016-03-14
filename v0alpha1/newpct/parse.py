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


# Parse page for results
def parse(self, data, mode, torrent_method):
    items = []
    with BS4Parser(data, 'html5lib') as html:
        torrent_table = html.find('table', id='categoryTable')
        torrent_rows = torrent_table.find_all('tr') if torrent_table else []

        # Continue only if at least one Release is found
        if len(torrent_rows) < 3:  # Headers + 1 Torrent + Pagination
            log.debug('Data returned from provider does not contain any torrents')
            return items

        labels = [label.get_text(strip=True) for label in torrent_rows[0].find_all('th')]

        # Skip column headers
        for row in torrent_rows[1:-1]:
            cells = row.find_all('td')

            torrent_row = row.find('a')
            title = self._processTitle(torrent_row.get('title', ''))
            download_url = torrent_row.get('href', '')
            if not all([title, download_url]):
                continue

            # Provider does not provide seeders/leechers
            seeders = 1
            leechers = 0
            torrent_size = cells[labels.index('Tamaño')].get_text(strip=True)

            item = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
            if mode != 'RSS':
                log.debug('Found result: {}'.format(title))

            items.append(item)


def get_url(self, url, post_data=None, params=None, timeout=30, **kwargs):  # pylint: disable=too-many-arguments
    """
    returns='content' when trying access to torrent info (For calling torrent client). Previously we must parse
    the URL to get torrent file
    """
    trickery = kwargs.pop('returns', '')
    if trickery == 'content':
        kwargs['returns'] = 'text'
        data = super(newpctProvider, self).get_url(url, post_data=post_data, params=params, timeout=timeout, kwargs=kwargs)
        url = re.search(r'http://tumejorserie.com/descargar/.+\.torrent', data, re.DOTALL).group()

    kwargs['returns'] = trickery
    return super(newpctProvider, self).get_url(url, post_data=post_data, params=params,
                                               timeout=timeout, kwargs=kwargs)


def download_result(self, result):
    """
    Save the result to disk.
    """

    # check for auth
    if not self.login():
        return False

    urls, filename = self._make_url(result)

    for url in urls:
        # Search results don't return torrent files directly, it returns show sheets so we must parse showSheet to access torrent.
        data = self.get_url(url, returns='text')
        url_torrent = re.search(r'http://tumejorserie.com/descargar/.+\.torrent', data, re.DOTALL).group()

        if url_torrent.startswith('http'):
            self.headers.update({'Referer': '/'.join(url_torrent.split('/')[:3]) + '/'})

        log.info('Downloading a result from {}'.format(url))

        if helpers.download_file(url_torrent, filename, session=self.session, headers=self.headers):
            if self._verify_download(filename):
                log.info('Saved result to {}'.format(filename))
                return True
            else:
                log.warn('Could not download {}'.format(url))
                helpers.remove_file_failed(filename)

    if len(urls):
        log.warn('Failed to download any results')

    return False

@staticmethod
def _processTitle(title):
    # Remove 'Mas informacion sobre ' literal from title
    title = title[22:]

    # Quality - Use re module to avoid case sensitive problems with replace
    title = re.sub(r'\[HDTV 1080p[^\[]*]', '1080p HDTV x264', title, flags=re.IGNORECASE)
    title = re.sub(r'\[HDTV 720p[^\[]*]', '720p HDTV x264', title, flags=re.IGNORECASE)
    title = re.sub(r'\[ALTA DEFINICION 720p[^\[]*]', '720p HDTV x264', title, flags=re.IGNORECASE)
    title = re.sub(r'\[HDTV]', 'HDTV x264', title, flags=re.IGNORECASE)
    title = re.sub(r'\[DVD[^\[]*]', 'DVDrip x264', title, flags=re.IGNORECASE)
    title = re.sub(r'\[BluRay 1080p[^\[]*]', '1080p BlueRay x264', title, flags=re.IGNORECASE)
    title = re.sub(r'\[BluRay MicroHD[^\[]*]', '1080p BlueRay x264', title, flags=re.IGNORECASE)
    title = re.sub(r'\[MicroHD 1080p[^\[]*]', '1080p BlueRay x264', title, flags=re.IGNORECASE)
    title = re.sub(r'\[BLuRay[^\[]*]', '720p BlueRay x264', title, flags=re.IGNORECASE)
    title = re.sub(r'\[BRrip[^\[]*]', '720p BlueRay x264', title, flags=re.IGNORECASE)
    title = re.sub(r'\[BDrip[^\[]*]', '720p BlueRay x264', title, flags=re.IGNORECASE)

    # Language
    title = re.sub(r'\[Spanish[^\[]*]', 'SPANISH AUDIO', title, flags=re.IGNORECASE)
    title = re.sub(r'\[Castellano[^\[]*]', 'SPANISH AUDIO', title, flags=re.IGNORECASE)
    title = re.sub(r'\[Español[^\[]*]', 'SPANISH AUDIO', title, flags=re.IGNORECASE)
    title = re.sub(r'\[AC3 5\.1 Español[^\[]*]', 'SPANISH AUDIO', title, flags=re.IGNORECASE)

    title += '-NEWPCT'

    return title.strip()
