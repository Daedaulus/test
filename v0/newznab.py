import logging
import re

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class NewznabProvider:

    def __init__(self, name, url, key='0', catIDs='5030,5040', search_mode='eponly',
                 search_fallback=False, enable_daily=True, enable_backlog=False):

        self.session = Session()

        self.url = url
        self.key = key

        self.search_mode = search_mode
        self.search_fallback = search_fallback
        self.enable_daily = enable_daily
        self.enable_backlog = enable_backlog

        # 0 in the key spot indicates that no key is needed
        self.needs_auth = self.key != '0'
        self.public = not self.needs_auth

        self.catIDs = catIDs if catIDs else '5030,5040'

        self.default = False

        self.caps = False
        self.cap_tv_search = None
        # self.cap_search = None
        # self.cap_movie_search = None
        # self.cap_audio_search = None

    def configStr(self):
        return self.name + '|' + self.url + '|' + self.key + '|' + self.catIDs + '|' + str(
            int(self.enabled)) + '|' + self.search_mode + '|' + str(int(self.search_fallback)) + '|' + str(
                int(self.enable_daily)) + '|' + str(int(self.enable_backlog))

    @staticmethod
    def get_providers_list(data):
        default_list = [x for x in [NewznabProvider._make_provider(x) for x in NewznabProvider._get_default_providers().split('!!!')] if x]
        providers_list = [x for x in [NewznabProvider._make_provider(x) for x in data.split('!!!')] if x]
        seen_values = set()
        providers_set = []

        for provider in providers_list:
            value = provider.name

            if value not in seen_values:
                providers_set.append(provider)
                seen_values.add(value)

        providers_list = providers_set
        providers_dict = dict(zip([x.name for x in providers_list], providers_list))

        for default in default_list:
            if not default:
                continue

            if default.name not in providers_dict:
                default.default = True
                providers_list.append(default)
            else:
                providers_dict[default.name].default = True
                providers_dict[default.name].name = default.name
                providers_dict[default.name].url = default.url
                providers_dict[default.name].needs_auth = default.needs_auth
                providers_dict[default.name].search_mode = default.search_mode
                providers_dict[default.name].search_fallback = default.search_fallback
                providers_dict[default.name].enable_daily = default.enable_daily
                providers_dict[default.name].enable_backlog = default.enable_backlog
                providers_dict[default.name].catIDs = default.catIDs

        return [x for x in providers_list if x]

    def image_name(self):
        if ek(os.path.isfile,
              ek(os.path.join, sickbeard.PROG_DIR, 'gui', sickbeard.GUI_NAME, 'images', 'providers',
                 self.get_id() + '.png')):
            return self.get_id() + '.png'
        return 'newznab.png'

    def set_caps(self, data):
        if not data:
            return

        def _parse_cap(tag):
            elm = data.find(tag)
            return elm.get('supportedparams', 'True') if elm and elm.get('available') else ''

        self.cap_tv_search = _parse_cap('tv-search')
        # self.cap_search = _parse_cap('search')
        # self.cap_movie_search = _parse_cap('movie-search')
        # self.cap_audio_search = _parse_cap('audio-search')

        # self.caps = any([self.cap_tv_search, self.cap_search, self.cap_movie_search, self.cap_audio_search])
        self.caps = any([self.cap_tv_search])

    def get_newznab_categories(self, just_caps=False):
        return_categories = []

        if not self._check_auth():
            return False, return_categories, 'Provider requires auth and your key is not set'

        url_params = {'t': 'caps'}
        if self.needs_auth and self.key:
            url_params['apikey'] = self.key

        data = self.session.get(urljoin(self.url, 'api'), params=url_params, returns='text')
        if not data:
            error_string = 'Error getting caps xml for [{}]'.format(self.name)
            log.warn(error_string)
            return False, return_categories, error_string

        with BS4Parser(data, 'html5lib') as html:
            if not html.find('categories'):
                error_string = 'Error parsing caps xml for [{}]'.format(self.name)
                log.debug(error_string)
                return False, return_categories, error_string

            self.set_caps(html.find('searching'))
            if just_caps:
                return

            for category in html('category'):
                if 'TV' in category.get('name', '') and category.get('id', ''):
                    return_categories.append({'id': category['id'], 'name': category['name']})
                    for subcat in category('subcat'):
                        if subcat.get('name', '') and subcat.get('id', ''):
                            return_categories.append({'id': subcat['id'], 'name': subcat['name']})

            return True, return_categories, ''

        error_string = 'Error getting xml for [{}]'.format(self.name)
        log.warn(error_string)
        return False, return_categories, error_string

    @staticmethod
    def _get_default_providers():
        # name|url|key|catIDs|enabled|search_mode|search_fallback|enable_daily|enable_backlog
        return 'NZB.Cat|https://nzb.cat/||5030,5040,5010|0|eponly|1|1|1!!!' + \
            'NZBGeek|https://api.nzbgeek.info/||5030,5040|0|eponly|0|0|0!!!' + \
            'NZBs.org|https://nzbs.org/||5030,5040|0|eponly|0|0|0!!!' + \
            'Usenet-Crawler|https://www.usenet-crawler.com/||5030,5040|0|eponly|0|0|0!!!' + \
            'DOGnzb|https://api.dognzb.cr/||5030,5040,5060,5070|0|eponly|0|1|1'

    def _check_auth(self):
        if self.needs_auth and not self.key:
            log.warn('Invalid api key. Check your settings')
            return False

        return True

    def _checkAuthFromData(self, data):
        if data('categories') + data('item'):
            return self._check_auth()

        try:
            err_desc = data.error.attrs['description']
            if not err_desc:
                raise ValueError('No error description')
        except (AttributeError, TypeError):
            return self._check_auth()

        log.info(ss(err_desc))

        return False

    @staticmethod
    def _make_provider(config):
        if not config:
            return None

        enable_backlog = 0
        enable_daily = 0
        search_fallback = 0
        search_mode = 'eponly'

        try:
            values = config.split('|')

            if len(values) == 9:
                name, url, key, category_ids, enabled, search_mode, search_fallback, enable_daily, enable_backlog = values
            else:
                name = values[0]
                url = values[1]
                key = values[2]
                category_ids = values[3]
                enabled = values[4]
        except ValueError:
            log.error('Skipping Newznab provider string: \'{}\', incorrect format'.format(config))
            return None

        new_provider = NewznabProvider(
            name, url, key=key, catIDs=category_ids, search_mode=search_mode, search_fallback=search_fallback,
            enable_daily=enable_daily, enable_backlog=enable_backlog
        )
        new_provider.enabled = enabled == '1'

        return new_provider

    def search(self, search_strings, age=0, ep_obj=None):
        results = []
        if not self._check_auth():
            return results

        # gingadaddy has no caps.
        if not self.caps and 'gingadaddy' not in self.url:
            self.get_newznab_categories(just_caps=True)

        if not self.caps and 'gingadaddy' not in self.url:
            return results

        for mode in search_strings:
            torznab = False
            search_params = {
                't': 'tvsearch' if 'tvdbid' in str(self.cap_tv_search) else 'search',
                'limit': 100,
                'offset': 0,
                'cat': self.catIDs.strip(', ') or '5030,5040',
                'maxage': sickbeard.USENET_RETENTION
            }

            if self.needs_auth and self.key:
                search_params['apikey'] = self.key

            if mode != 'RSS':
                if search_params['t'] == 'tvsearch':
                    search_params['tvdbid'] = ep_obj.show.indexerid

                    if ep_obj.show.air_by_date or ep_obj.show.sports:
                        date_str = str(ep_obj.airdate)
                        search_params['season'] = date_str.partition('-')[0]
                        search_params['ep'] = date_str.partition('-')[2].replace('-', '/')
                    else:
                        search_params['season'] = ep_obj.scene_season
                        search_params['ep'] = ep_obj.scene_episode

                if mode == 'Season':
                    search_params.pop('ep', '')

            items = []
            log.debug('Search Mode: {}'.format(mode))
            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {}'.format(search_string.decode('utf-8')))

                    if search_params['t'] != 'tvsearch':
                        search_params['q'] = search_string

                time.sleep(cpu_presets[sickbeard.CPU_PRESET])
                data = self.session.get(urljoin(self.url, 'api'), params=search_params, returns='text')
                if not data:
                    break

                with BS4Parser(data, 'html5lib') as html:
                    if not self._checkAuthFromData(html):
                        break

                    try:
                        torznab = 'xmlns:torznab' in html.rss.attrs
                    except AttributeError:
                        torznab = False

                    for item in html('item'):
                        try:
                            title = item.title.get_text(strip=True)
                            download_url = None
                            if item.link:
                                if validators.url(item.link.get_text(strip=True)):
                                    download_url = item.link.get_text(strip=True)
                                elif validators.url(item.link.next.strip()):
                                    download_url = item.link.next.strip()

                            if not download_url and item.enclosure:
                                if validators.url(item.enclosure.get('url', '').strip()):
                                    download_url = item.enclosure.get('url', '').strip()

                            if not (title and download_url):
                                continue

                            seeders = leechers = None
                            if 'gingadaddy' in self.url:
                                size_regex = re.search(r'\d*.?\d* [KMGT]B', str(item.description))
                                item_size = size_regex.group() if size_regex else -1
                            else:
                                item_size = item.size.get_text(strip=True) if item.size else -1
                                for attr in item('newznab:attr') + item('torznab:attr'):
                                    item_size = attr['value'] if attr['name'] == 'size' else item_size
                                    seeders = attr['value'] if attr['name'] == 'seeders' else seeders
                                    leechers = attr['value'] if attr['name'] == 'peers' else leechers

                            if not item_size or (torznab and (seeders is None or leechers is None)):
                                continue

                            result = {'title': title, 'link': download_url, 'size': torrent_size, 'seeders': seeders, 'leechers': leechers}
                            items.append(result)
                        except Exception:
                            continue

                # Since we arent using the search string,
                # break out of the search string loop
                if 'tvdbid' in search_params:
                    break

            results += items

        return results

    def _get_size(self, item):
        return item.get('size', -1)
