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


class TNTVillageProvider:

    def __init__(self, name, **kwargs):
        # Name
        self.name = name

        # Connection
        self.session = kwargs.pop('session', Session())

        # URLs
        self.url = 'http://forum.tntvillage.scambioetico.org'
        self.urls = {
            'base': self.url,
            'login': urljoin(self.url, 'index.php?act=Login&CODE=01'),
            'search': urljoin(self.url, '?act=allreleases&%s'),
            'search_page': urljoin(self.url, '?act=allreleases&st={0}&{1}'),
            'detail': urljoin(self.url, 'index.php?showtopic=%s'),
            'download': urljoin(self.url, 'index.php?act=Attach&type=post&id=%s')
        }

        # Credentials
        self.username = None
        self.password = None
        self._uid = None
        self._hash = None
        self.login_params = {
            'UserName': self.username,
            'PassWord': self.password,
            'CookieDate': 1,
            'submit': 'Connettiti al Forum'
        }

        # Torrent Stats
        self.min_seed = None
        self.min_leech = None

        # Proper Strings
        self.proper_strings = [
            'PROPER',
            'REPACK',
        ]

        # Search Params

        # Categories
        self.category_dict = {
            'Serie TV': 29,
            'Cartoni': 8,
            'Anime': 7,
            'Programmi e Film TV': 1,
            'Documentari': 14,
            'All': 0
        }
        self.categories = 'cat=29'
        self.sub_string = [
            'sub',
            'softsub'
        ]
        self.hdtext = [
            ' - Versione 720p',
            ' Versione 720p',
            ' V 720p',
            ' V 720',
            ' V HEVC',
            ' V  HEVC',
            ' V 1080',
            ' Versione 1080p',
            ' 720p HEVC',
            ' Ver 720',
            ' 720p HEVC',
            ' 720p',
        ]

        # Proper Strings

        # Options
        self.cat = None
        self.engrelease = None
        self.page = 10
        self.subtitle = None

    # Search page
    def search(
        self,
        search_strings,
        search_params,
        torrent_method=None,
        ep_obj=None,
        *args, **kwargs
    ):
        results = []

        if not self.login():
            return results

        self.categories = 'cat=' + str(self.cat)

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            log.debug('Search Mode: {}'.format(mode))

            for search_string in search_strings[mode]:

                if mode == 'RSS':
                    self.page = 2

                last_page = 0
                y = int(self.page)

                if search_string == '':
                    continue

                search_string = str(search_string).replace('.', ' ')

                for x in range(0, y):
                    z = x * 20
                    if last_page:
                        break

                    if mode != 'RSS':
                        log.debug('Search string: {}'.format(search_string.decode('utf-8')))
                        search_url = (self.urls['search_page'] + '&filter={2}').format(z, self.categories, search_string)
                    else:
                        search_url = self.urls['search_page'].format(z, self.categories)

                    data = self.session.get(search_url).text
                    if not data:
                        log.debug('No data returned from provider')
                        continue

                    try:
                        with BS4Parser(data, 'html5lib') as html:
                            torrent_table = html.find('table', attrs={'class': 'copyright'})
                            torrent_rows = torrent_table('tr') if torrent_table else []

                            # Continue only if at least one Release is found
                            if len(torrent_rows) < 3:
                                log.debug('Data returned from provider does not contain any torrents')
                                last_page = 1
                                continue

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

                    except Exception:
                        log.error('Failed parsing provider. Traceback: %s' % traceback.format_exc())

                results += items

        return results

    # Parse page for results
    def parse(self):
        raise NotImplementedError

    # Log in
    def login(self, login_params):
        if len(self.session.cookies) >= 3:
            if self.session.cookies.get('pass_hash', '') not in ('0', 0) and self.session.cookies.get('member_id') not in ('0', 0):
                return True

        response = self.session.post(self.urls['login'], data=login_params).text
        if not response:
            log.warn('Unable to connect to provider')
            return False

        # Invalid username and password combination
        if re.search('Sono stati riscontrati i seguenti errori', response) or re.search('<title>Connettiti</title>', response):
            log.warn('Invalid username or password. Check your settings')
            return False

        return True

    # Validate login
    def check_auth(self):
        if not self.username or not self.password:
            raise Exception('Your authentication credentials for ' + self.name + ' are missing, check your config.')
        return True

    @staticmethod
    def _reverse_quality(quality):

        quality_string = ''

        if quality == Quality.SDTV:
            quality_string = ' HDTV x264'
        if quality == Quality.SDDVD:
            quality_string = ' DVDRIP'
        elif quality == Quality.HDTV:
            quality_string = ' 720p HDTV x264'
        elif quality == Quality.FULLHDTV:
            quality_string = ' 1080p HDTV x264'
        elif quality == Quality.RAWHDTV:
            quality_string = ' 1080i HDTV mpeg2'
        elif quality == Quality.HDWEBDL:
            quality_string = ' 720p WEB-DL h264'
        elif quality == Quality.FULLHDWEBDL:
            quality_string = ' 1080p WEB-DL h264'
        elif quality == Quality.HDBLURAY:
            quality_string = ' 720p Bluray x264'
        elif quality == Quality.FULLHDBLURAY:
            quality_string = ' 1080p Bluray x264'

        return quality_string

    @staticmethod
    def _episode_quality(torrent_rows):
        file_quality = ''

        img_all = (torrent_rows('td'))[1]('img')

        if len(img_all) > 0:
            for img_type in img_all:
                try:
                    file_quality = file_quality + ' ' + img_type['src'].replace('style_images/mkportal-636/', '').replace('.gif', '').replace('.png', '')
                except Exception:
                    log.error('Failed parsing quality. Traceback: %s' % traceback.format_exc())

        else:
            file_quality = (torrent_rows('td'))[1].get_text()
            log.debug('Episode quality: %s' % file_quality)

        def check_name(options, func):
            return func([re.search(option, file_quality, re.I) for option in options])

        dvd_options = check_name(['dvd', 'dvdrip', 'dvdmux', 'DVD9', 'DVD5'], any)
        bluray_options = check_name(['BD', 'BDmux', 'BDrip', 'BRrip', 'Bluray'], any)
        sd_options = check_name(['h264', 'divx', 'XviD', 'tv', 'TVrip', 'SATRip', 'DTTrip', 'Mpeg2'], any)
        hd_options = check_name(['720p'], any)
        full_hd = check_name(['1080p', 'fullHD'], any)

        if len(img_all) > 0:
            file_quality = (torrent_rows('td'))[1].get_text()

        webdl = check_name(['webdl', 'webmux', 'webrip', 'dl-webmux', 'web-dlmux', 'webdl-mux', 'web-dl', 'webdlmux', 'dlmux'], any)

        if sd_options and not dvd_options and not full_hd and not hd_options:
            return Quality.SDTV
        elif dvd_options:
            return Quality.SDDVD
        elif hd_options and not bluray_options and not full_hd and not webdl:
            return Quality.HDTV
        elif not hd_options and not bluray_options and full_hd and not webdl:
            return Quality.FULLHDTV
        elif hd_options and not bluray_options and not full_hd and webdl:
            return Quality.HDWEBDL
        elif not hd_options and not bluray_options and full_hd and webdl:
            return Quality.FULLHDWEBDL
        elif bluray_options and hd_options and not full_hd:
            return Quality.HDBLURAY
        elif bluray_options and full_hd and not hd_options:
            return Quality.FULLHDBLURAY
        else:
            return Quality.UNKNOWN

    def _is_italian(self, torrent_rows):

        name = str(torrent_rows('td')[1].find('b').find('span'))
        if not name or name == 'None':
            return False

        sub_found = italian = False
        for sub in self.sub_string:
            if re.search(sub, name, re.I):
                sub_found = True
            else:
                continue

            if re.search('ita', name.split(sub)[0], re.I):
                log.debug('Found Italian release:  ' + name)
                italian = True
                break

        if not sub_found and re.search('ita', name, re.I):
            log.debug('Found Italian release:  ' + name)
            italian = True

        return italian

    @staticmethod
    def _is_english(torrent_rows):

        name = str(torrent_rows('td')[1].find('b').find('span'))
        if not name or name == 'None':
            return False

        english = False
        if re.search('eng', name, re.I):
            log.debug('Found English release:  ' + name)
            english = True

        return english

    @staticmethod
    def _is_season_pack(name):
        try:
            parse_result = NameParser(tryIndexers=True).parse(name)
        except (InvalidNameException, InvalidShowException) as error:
            log.debug('{}'.format(error))
            return False

        main_db_con = db.DBConnection()
        sql_selection = 'select count(*) as count from tv_episodes where showid = ? and season = ?'
        episodes = main_db_con.select(sql_selection, [parse_result.show.indexerid, parse_result.season_number])
        if int(episodes[0]['count']) == len(parse_result.episode_numbers):
            return True
