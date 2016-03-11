from contextlib import suppress

from .provider import Provider
from .search import search
from .parse import parse

with suppress(ImportError):
    from .auth import login
with suppress(ImportError):
    from .auth import check_auth

provider = Provider
provider.search = search
provider.parse = parse

with suppress(NameError):
    provider.login = login
with suppress(NameError):
    provider.check_auth = check_auth
