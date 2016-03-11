import logging
from v0alpha1 import (
    abnormal,
    alpharatio,
    bitsnoop,
    btdigg,
    cpasbien,
    extratorrent,
    gftracker,
    iptorrents,
    kat,
    limetorrents,
    nyaatorrents,
    phxbit,
    rarbg,
    thepiratebay,
    tntvillage,
    tokyotoshokan,
    torrentbytes,
    torrentleech,
    torrentproject,
    torrentz,
)
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

bitsnoop = bitsnoop.provider('BitSnoop')
btdigg = btdigg.provider('BTDigg')
cpasbien = cpasbien.provider('CPasBien')
extratorrent = extratorrent.provider('ExtraTorrent')
iptorrents = iptorrents.provider('IPTorrents')
kat = kat.provider('KickAss')
limetorrents = limetorrents.provider('Lime')
nyaatorrents = nyaatorrents.provider('Nyaa')
rarbg = rarbg.provider('RARBg')
thepiratebay = thepiratebay.provider('ThePirateBay')
tokyotoshokan = tokyotoshokan.provider('TokyoToshokan')
torrentproject = torrentproject.provider('TorrentProject')
torrentz = torrentz.provider('Torrentz')

search = {'RSS': ['', ]}
provider_list = [
    # # *********** IN PROGRESS ***********
    # # PUBLIC
    kat,  # No attribute show
    nyaatorrents,  # No attribute show
    tokyotoshokan,  # No attribute show

    # # LOGIN REQUIRED
    # rarbg,  # Login Required
    # torrentbytes,  # Login Required
    # torrentleech,  # Login Required
    # iptorrents,  # Login Required

    # # LOGIN FAILED
    # alpharatio,  # Login failed
    # tntvillage,  # Login failed

    # # CLOUD FLARE
    # bitsnoop,  # cloud flare
    # btdigg,  # cloud flare
    # cpasbien,  # cloud flare

    # # *********** WORKING ***********
    # # WORKING PUBLIC
    # extratorrent,
    # limetorrents,
    # thepiratebay,
    # torrentproject,
    # torrentz,

    # # WORKING LOGIN REQUIRED
    # gftracker,  # Login Required

    # # WORKING BORROWED LOGIN REQUIRED
    # abnormal,  # Login Required
    # phxbit,  # Login Required
]

for p in provider_list:
    log.debug('************ Provider: {name} ************'.format(name=p.name))
    x = 0
    search_params = {}
    if hasattr(p, 'search_params'):
        search_params = p.search_params
    for data in p.search(
          search_url=p.urls.get('search', p.url),
          search_strings=search,
          search_params=search_params,
          torrent_method=None
    ):
        ext = 'txt'
        if 'xml' in data.text:
            ext = 'xml'
        if 'html' in data.text:
            ext = 'html'
        with open('{location}{prov}.{num}.{type}'.format(location='results\\', prov=p.name, num=x, type=ext), 'wb') as result:
            result.write(data.content)
        x += 1

# from bs4 import BeautifulSoup, Doctype
#
# for each in [
#     # 'BTDigg',
#     'ExtraTorrent',
#     'ThePirateBay',
#     'TorrentProject',
# ]:
#     with open('results\{}.0.xml'.format(each), 'rb') as source:
#         data = BeautifulSoup(source, 'html5lib')
#         print(data.contents[0])
