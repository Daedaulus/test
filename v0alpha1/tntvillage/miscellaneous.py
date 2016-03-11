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


def _is_english(torrent_rows):

    name = str(torrent_rows('td')[1].find('b').find('span'))
    if not name or name == 'None':
        return False

    english = False
    if re.search('eng', name, re.I):
        log.debug('Found English release:  ' + name)
        english = True

    return english


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
