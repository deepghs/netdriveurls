from hbutils.system import urlsplit

from .base import URLRedirectSolver


class BunkrCDNResolver(URLRedirectSolver):
    @classmethod
    def is_solvable(cls, url: str) -> bool:
        split = urlsplit(url)
        return len(split.host.split('.')) >= 3 and \
            split.host.split('.')[-2] in {'bunkr', 'bunkrrr'} and \
            split.host.split('.')[-3].startswith('cdn')
