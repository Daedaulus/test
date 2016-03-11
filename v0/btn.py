import logging
# import re

from requests import Session
# from requests.compat import urljoin
# from requests.utils import dict_from_cookiejar
#
# from v0 import BS4Parser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class BTNProvider:

    def __init__(self):

        self.session = Session()

        self.supports_absolute_numbering = True

        self.api_key = None

        self.cache = BTNCache()  # Only poll BTN every 15 minutes max

        self.urls = {'base_url': 'http://api.btnapps.net',
                     'website': 'http://broadcasthe.net/', }

        self.url = self.urls['website']

    def _check_auth(self):
        if not self.api_key:
            log.warn('Invalid api key. Check your settings')

        return True

    def _checkAuthFromData(self, parsedJSON):

        if parsedJSON is None:
            return self._check_auth()

        if 'api-error' in parsedJSON:
            log.debug('Incorrect authentication credentials: % s' % parsedJSON['api-error'])
            raise Exception('Your authentication credentials for ' + self.name + ' are incorrect, check your config.')

        return True

    def search(self, search_params, age=0, ep_obj=None):

        self._check_auth()

        results = []
        params = {}
        apikey = self.api_key

        # age in seconds
        if age:
            params['age'] = '<=' + str(int(age))

        if search_params:
            params.update(search_params)
            log.debug('Search string: %s' % search_params)

        parsedJSON = self._api_call(apikey, params)
        if not parsedJSON:
            log.debug('No data returned from provider')
            return results

        if self._checkAuthFromData(parsedJSON):

            if 'torrents' in parsedJSON:
                found_torrents = parsedJSON['torrents']
            else:
                found_torrents = {}

            # We got something, we know the API sends max 1000 results at a time.
            # See if there are more than 1000 results for our query, if not we
            # keep requesting until we've got everything.
            # max 150 requests per hour so limit at that. Scan every 15 minutes. 60 / 15 = 4.
            max_pages = 150
            results_per_page = 1000

            if 'results' in parsedJSON and int(parsedJSON['results']) >= results_per_page:
                pages_needed = int(math.ceil(int(parsedJSON['results']) / results_per_page))
                if pages_needed > max_pages:
                    pages_needed = max_pages

                # +1 because range(1,4) = 1, 2, 3
                for page in range(1, pages_needed + 1):
                    parsedJSON = self._api_call(apikey, params, results_per_page, page * results_per_page)
                    # Note that this these are individual requests and might time out individually. This would result in 'gaps'
                    # in the results. There is no way to fix this though.
                    if 'torrents' in parsedJSON:
                        found_torrents.update(parsedJSON['torrents'])

            for _, torrent_info in found_torrents.iteritems():
                (title, url) = self._get_title_and_url(torrent_info)

                if title and url:
                    log.debug('Found result: %s ' % title)
                    results.append(torrent_info)

        return results

    def _api_call(self, apikey, params=None, results_per_page=1000, offset=0):

        server = jsonrpclib.Server(self.urls['base_url'])
        parsedJSON = {}

        try:
            parsedJSON = server.getTorrents(apikey, params or {}, int(results_per_page), int(offset))
            time.sleep(cpu_presets[sickbeard.CPU_PRESET])

        except jsonrpclib.jsonrpc.ProtocolError as error:
            if error.message == 'Call Limit Exceeded':
                log.warn('You have exceeded the limit of 150 calls per hour, per API key which is unique to your user account')
            else:
                log.error('JSON-RPC protocol error while accessing provicer. Error: %s ' % repr(error))
            parsedJSON = {'api-error': ex(error)}
            return parsedJSON

        except socket.timeout:
            log.warn('Timeout while accessing provider')

        except socket.error as error:
            # Note that sometimes timeouts are thrown as socket errors
            log.warn('Socket error while accessing provider. Error: %s ' % error[1])

        except Exception as error:
            errorstring = str(error)
            if errorstring.startswith('<') and errorstring.endswith('>'):
                errorstring = errorstring[1:-1]
            log.warn('Unknown error while accessing provider. Error: %s ' % errorstring)

        return parsedJSON

    @staticmethod
    def _get_title_and_url(parsedJSON):

        # The BTN API gives a lot of information in response,
        # however SickRage is built mostly around Scene or
        # release names, which is why we are using them here.

        if 'ReleaseName' in parsedJSON and parsedJSON['ReleaseName']:
            title = parsedJSON['ReleaseName']

        else:
            # If we don't have a release name we need to get creative
            title = ''
            if 'Series' in parsedJSON:
                title += parsedJSON['Series']
            if 'GroupName' in parsedJSON:
                title += '.' + parsedJSON['GroupName'] if title else parsedJSON['GroupName']
            if 'Resolution' in parsedJSON:
                title += '.' + parsedJSON['Resolution'] if title else parsedJSON['Resolution']
            if 'Source' in parsedJSON:
                title += '.' + parsedJSON['Source'] if title else parsedJSON['Source']
            if 'Codec' in parsedJSON:
                title += '.' + parsedJSON['Codec'] if title else parsedJSON['Codec']
            if title:
                title = title.replace(' ', '.')

        url = None
        if 'DownloadURL' in parsedJSON:
            url = parsedJSON['DownloadURL']
            if url:
                # unescaped / is valid in JSON, but it can be escaped
                url = url.replace('\\/', '/')

        return title, url

    @staticmethod
    def _get_season_search_strings(ep_obj):
        search_params = []
        current_params = {'category': 'Season'}

        # Search for entire seasons: no need to do special things for air by date or sports shows
        if ep_obj.show.air_by_date or ep_obj.show.sports:
            # Search for the year of the air by date show
            current_params['name'] = str(ep_obj.airdate).split('-')[0]
        elif ep_obj.show.is_anime:
            current_params['name'] = '%d' % ep_obj.scene_absolute_number
        else:
            current_params['name'] = 'Season ' + str(ep_obj.scene_season)

        # search
        if ep_obj.show.indexer == 1:
            current_params['tvdb'] = ep_obj.show.indexerid
            search_params.append(current_params)
        else:
            name_exceptions = list(
                set(scene_exceptions.get_scene_exceptions(ep_obj.show.indexerid) + [ep_obj.show.name]))
            for name in name_exceptions:
                # Search by name if we don't have tvdb id
                current_params['series'] = sanitizeSceneName(name)
                search_params.append(current_params)

        return search_params

    @staticmethod
    def _get_episode_search_strings(ep_obj):

        if not ep_obj:
            return [{}]

        to_return = []
        search_params = {'category': 'Episode'}

        # episode
        if ep_obj.show.air_by_date or ep_obj.show.sports:
            date_str = str(ep_obj.airdate)

            # BTN uses dots in dates, we just search for the date since that
            # combined with the series identifier should result in just one episode
            search_params['name'] = date_str.replace('-', '.')
        elif ep_obj.show.anime:
            search_params['name'] = '%i' % int(ep_obj.scene_absolute_number)
        else:
            # Do a general name search for the episode, formatted like SXXEYY
            search_params['name'] = '{ep}'.format(ep=episode_num(ep_obj.scene_season, ep_obj.scene_episode))

        # search
        if ep_obj.show.indexer == 1:
            search_params['tvdb'] = ep_obj.show.indexerid
            to_return.append(search_params)
        else:
            # add new query string for every exception
            name_exceptions = list(
                set(scene_exceptions.get_scene_exceptions(ep_obj.show.indexerid) + [ep_obj.show.name]))
            for cur_exception in name_exceptions:
                search_params['series'] = sanitizeSceneName(cur_exception)
                to_return.append(search_params)

        return to_return

    def _doGeneralSearch(self, search_string):
        # 'search' looks as broad is it can find. Can contain episode overview and title for example,
        # use with caution!
        return self.search({'search': search_string})

    def find_propers(self, search_date=None):
        results = []

        search_terms = ['%.proper.%', '%.repack.%']

        for term in search_terms:
            for item in self.search({'release': term}, age=4 * 24 * 60 * 60):
                if item['Time']:
                    try:
                        result_date = datetime.fromtimestamp(float(item['Time']))
                    except TypeError:
                        result_date = None

                    if result_date:
                        if not search_date or result_date > search_date:
                            title, url = self._get_title_and_url(item)
                            results.append(classes.Proper(title, url, result_date, self.show))

        return results


class BTNCache:
    def _getRSSData(self):
        # Get the torrents uploaded since last check.
        seconds_since_last_update = math.ceil(time.time() - time.mktime(self._getLastUpdate().timetuple()))

        # default to 15 minutes
        seconds_minTime = self.minTime * 60
        if seconds_since_last_update < seconds_minTime:
            seconds_since_last_update = seconds_minTime

        # Set maximum to 24 hours (24 * 60 * 60 = 86400 seconds) of 'RSS' data search, older things will need to be done through backlog
        if seconds_since_last_update > 86400:
            log.debug('The last known successful update was more than 24 hours ago, only trying to fetch the last 24 hours!')
            seconds_since_last_update = 86400

        self.search_params = None  # BTN cache does not use search params
        return {'entries': self.search(search_params=self.search_params, age=seconds_since_last_update)}
