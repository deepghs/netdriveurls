from typing import Optional
from urllib.parse import urljoin

import requests
from hbutils.system import urlsplit
from urlobject import URLObject

from .base import StandaloneResolver
from ..utils import get_requests_session


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


def redirect_cyberdrop(url: str, session: Optional[requests.Session] = None):
    session = session or get_requests_session()
    resp = session.head(url)
    resp.raise_for_status()
    return urljoin(resp.url, resp.headers['Location'])


class CyberDropDirectResolver(StandaloneResolver):
    @classmethod
    def resolve(cls, url: str) -> str:
        session = get_requests_session()
        return redirect_cyberdrop(url, session=session)

    @classmethod
    def is_solvable(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')) == ('cyberdrop', 'me') and \
            len(split.path_segments) == 2
