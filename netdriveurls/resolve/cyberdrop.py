from hbutils.system import urlsplit
from urlobject import URLObject

from .base import StandaloneResolver, URLRedirectSolver


class CyberDropEResolver(StandaloneResolver):
    @classmethod
    def resolve(cls, url: str) -> str:
        obj = URLObject(url)
        return str(obj.with_path('/'.join(['', 'f', *obj.path.segments[1:]])))

    @classmethod
    def is_solvable(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')) == ('cyberdrop', 'me') and \
            tuple(split.path_segments[1:2]) == ('e',)


class CyberDropDirectResolver(URLRedirectSolver):
    @classmethod
    def is_solvable(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')) == ('cyberdrop', 'me') and \
            len(split.path_segments) == 2
