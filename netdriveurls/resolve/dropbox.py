from urllib.parse import urljoin

from hbutils.system import urlsplit

from .base import StandaloneResolver
from ..utils import get_requests_session


class DropBoxSResolver(StandaloneResolver):
    @classmethod
    def resolve(cls, url: str) -> str:
        session = get_requests_session()
        resp = session.head(url)
        resp.raise_for_status()
        return urljoin(resp.url, resp.headers['Location'])

    @classmethod
    def is_solvable(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('dropbox', 'com') and \
            tuple(split.path_segments[1:2]) == ('s',)


class DropBoxSHResolver(StandaloneResolver):
    @classmethod
    def resolve(cls, url: str) -> str:
        session = get_requests_session()
        resp = session.head(url)
        resp.raise_for_status()
        return urljoin(resp.url, resp.headers['Location'])

    @classmethod
    def is_solvable(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('dropbox', 'com') and \
            tuple(split.path_segments[1:2]) == ('sh',)
