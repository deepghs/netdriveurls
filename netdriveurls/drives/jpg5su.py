import os
from typing import Optional
from urllib.parse import urljoin

import requests
from hbutils.system import urlsplit
from pyquery import PyQuery as pq

from .base import StandaloneFileNetDriveDownloadSession
from ..utils import get_requests_session, download_file


def get_direct_url_for_jpg5su(url: str, session: Optional[requests.Session] = None):
    split = urlsplit(url)
    assert tuple(split.host.split('.')[-2:]) == ('jpg5', 'su'), f'Invalid host: {split.host!r}'
    assert tuple(split.path_segments[1:2]) == ('img',), f'Invalid path: {url!r}'

    session = session or get_requests_session()
    resp = session.get(url)
    resp.raise_for_status()

    page = pq(resp.text)
    url = urljoin(resp.url, page('[property="og:image"]').attr('content'))
    return url


class JPG5SuFileDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'jpg5su_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        direct_url = get_direct_url_for_jpg5su(self.page_url, session=session)
        _, ext = os.path.splitext(urlsplit(direct_url).filename.lower())
        filename = os.path.join(dst_dir, f'{self.resource_id}{ext}')
        download_file(direct_url, filename=filename, session=session)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('jpg5', 'su') and \
            tuple(split.path_segments[1:2]) == ('img',)
