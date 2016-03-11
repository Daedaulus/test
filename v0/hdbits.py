import logging
import re

from requests import Session
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class HDBitsProvider:

    def __init__(self):

        self.session = Session()

        # Credentials
        self.username = None
        self.passkey = None

        self.cache = HDBitsCache(self, min_time=15)  # only poll HDBits every 15 minutes max

        self.url = 'https://hdbits.org'
        self.urls = {
            'search': urljoin(self.url, '/api/torrents'),
            'rss': urljoin(self.url, '/api/torrents'),
            'download': urljoin(self.url, '/download.php')
        }

    def _check_auth(self):

        if not self.username or not self.passkey:
            raise Exception('Your authentication credentials for ' + self.name + ' are missing, check your config.')

        return True

    def _checkAuthFromData(self, parsedJSON):

        if 'status' in parsedJSON and 'message' in parsedJSON:
            if parsedJSON.get('status') == 5:
                log.warn('Invalid username or password. Check your settings')

        return True

    def _get_season_search_strings(self, ep_obj):
        season_search_string = [self._make_post_data_JSON(show=ep_obj.show, season=ep_obj)]
        return season_search_string

    def _get_episode_search_strings(self, ep_obj, add_string=''):
        episode_search_string = [self._make_post_data_JSON(show=ep_obj.show, episode=ep_obj)]
        return episode_search_string

    def _get_title_and_url(self, item):
        title = item.get('name', '').replace(' ', '.')
        url = self.urls['download'] + '?' + urlencode({'id': item['id'], 'passkey': self.passkey})

        return title, url

    def search(self, search_params, age=0, ep_obj=None):

        # FIXME
        results = []

        log.debug('Search string: %s' % search_params)

        self._check_auth()

        parsedJSON = self.session.post(self.urls['search'], data=search_params, returns='json')
        if not parsedJSON:
            return []

        if self._checkAuthFromData(parsedJSON):
            if parsedJSON and 'data' in parsedJSON:
                items = parsedJSON['data']
            else:
                log.error('Resulting JSON from provider isn\'t correct, not parsing it')
                items = []

            for item in items:
                results.append(item)
        # FIXME SORTING
        return results

    def find_propers(self, search_date=None):
        results = []

        search_terms = [' proper ', ' repack ']

        for term in search_terms:
            for item in self.search(self._make_post_data_JSON(search_term=term)):
                if item['utadded']:
                    try:
                        result_date = datetime.datetime.fromtimestamp(int(item['utadded']))
                    except Exception:
                        result_date = None

                    if result_date:
                        if not search_date or result_date > search_date:
                            title, url = self._get_title_and_url(item)
                            results.append(classes.Proper(title, url, result_date, self.show))

        return results

    def _make_post_data_JSON(self, show=None, episode=None, season=None, search_term=None):

        post_data = {
            'username': self.username,
            'passkey': self.passkey,
            'category': [2],
            # TV Category
        }

        if episode:
            if show.air_by_date:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'episode': str(episode.airdate).replace('-', '|')
                }
            elif show.sports:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'episode': episode.airdate.strftime('%b')
                }
            elif show.anime:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'episode': '%i' % int(episode.scene_absolute_number)
                }
            else:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'season': episode.scene_season,
                    'episode': episode.scene_episode
                }

        if season:
            if show.air_by_date or show.sports:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'season': str(season.airdate)[:7],
                }
            elif show.anime:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'season': '%d' % season.scene_absolute_number,
                }
            else:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'season': season.scene_season,
                }

        if search_term:
            post_data['search'] = search_term

        return json.dumps(post_data)


class HDBitsCache:
    def _getRSSData(self):
        self.search_params = None  # HDBits cache does not use search_params so set it to None
        results = []

        try:
            parsedJSON = self.session.post(self.urls['rss'], data=self._make_post_data_JSON(), returns='json')

            if self._checkAuthFromData(parsedJSON):
                results = parsedJSON['data']
        except Exception:
            pass

        return {'entries': results}
