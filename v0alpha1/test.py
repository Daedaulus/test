from v0alpha1.bitsnoop import provider, search
bitsnoop = provider.BitSnoopProvider('BitSnoop')
bitsnoop.search = search.search

from v0alpha1.btdigg import provider, search
btdigg = provider.BTDiggProvider('BTDigg')
btdigg.search = search.search

from v0alpha1.cpasbien import provider, search
cpasbien = provider.CPasBienProvider('CPasBien')
cpasbien.search = search.search

from v0alpha1.extratorrent import provider, search
extratorrent = provider.ExtraTorrentProvider('ExtraTorrent')
extratorrent.search = search.search

from v0alpha1.iptorrents import provider, search
iptorrent = provider.IPTorrentsProvider('IPTorrents')
iptorrent.search = search.search

from v0alpha1.kat import provider, search
kat = provider.KatProvider('KickAssTorrents')
kat.search = search.search

from v0alpha1.limetorrents import provider, search
limetorrents = provider.LimeTorrentsProvider('LimeTorrents')
limetorrents.search = search.search

from v0alpha1.nyaatorrents import provider, search
nyaatorrents = provider.NyaaProvider('Nyaa')
nyaatorrents.search = search.search

from v0alpha1.thepiratebay import provider, search
thepiratebay = provider.ThePirateBayProvider('ThePirateBay')
thepiratebay.search = search.search

from v0alpha1.tokyotoshokan import provider, search
tokyotoshokan = provider.TokyoToshokanProvider('Tokyo')
tokyotoshokan.search = search.search

from v0alpha1.torrentproject import provider, search
torrentproject = provider.TorrentProjectProvider('TorrentProject')
torrentproject.search = search.search

import logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

from v0 import BS4Parser

search = {'RSS': ['']}
provider_list = [
    bitsnoop,
    btdigg,
    cpasbien,
    extratorrent,
    thepiratebay,
    # torrentproject,
    # tokyotoshokan,
]

for p in provider_list:
    log.debug('************ Provider: {name} ************'.format(name=p.name))
    x = 0
    search_params = {}
    if hasattr(p, 'search_params'):
        search_params = p.search_params
    for data in p.search(p, search, search_params, None):
        ext = 'txt'
        if 'html' in data.text:
            ext = 'html'
        if 'xml' in data.text:
            ext = 'xml'
        with open('{location}{prov}.{num}.{type}'.format(location='results\\', prov=p.name, num=x, type=ext), 'wb') as result:
            result.write(data.content)
        x += 1
