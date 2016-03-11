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
