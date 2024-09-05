import os.path
from typing import Optional
from urllib.parse import urljoin

import requests
from hbutils.system import urlsplit
from pyquery import PyQuery as pq

from .base import StandaloneFileNetDriveDownloadSession
from ..utils import get_requests_session, download_file


def get_direct_url_for_saint2(url: str, session: Optional[requests.Session] = None):
    split = urlsplit(url)
    assert tuple(split.host.split('.')[-2:]) == ('saint2', 'su'), f'Invalid host: {split.host!r}'
    assert tuple(split.path_segments[1:2]) == ('embed',), f'Invalid path: {url!r}'

    session = session or get_requests_session()
    resp = session.get(url)
    resp.raise_for_status()

    page = pq(resp.text)
    video_url = urljoin(resp.url, page('video source').attr('src'))
    return video_url


class Saint2EmbedDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url: str):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'saint2_embed_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session(headers={'Referer': 'https://saint2.su/'})
        url = get_direct_url_for_saint2(self.page_url, session=session)
        _, ext = os.path.splitext(urlsplit(url).filename.lower())
        dst_file = os.path.join(dst_dir, f'{self.resource_id}{ext}')
        download_file(url, filename=dst_file, session=session)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('saint2', 'su') and \
            tuple(split.path_segments[1:2]) == ('embed',)
