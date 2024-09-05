import glob
import os.path
import zipfile
from typing import Optional
from urllib.parse import urljoin

import requests
from hbutils.system import urlsplit, TemporaryDirectory
from pyquery import PyQuery as pq
from urlobject import URLObject

from .base import StandaloneFileNetDriveDownloadSession, NetDriveDownloadSession, ResourceInvalidError
from ..utils import get_requests_session, download_file


def get_direct_url_for_pixhost(url: str, session: Optional[requests.Session] = None):
    session = session or get_requests_session()
    resp = session.get(url)
    resp.raise_for_status()

    page = pq(resp.text)
    relurl = page('.image img#image').attr('src')
    if relurl:
        return urljoin(resp.url, relurl)
    else:
        raise ResourceInvalidError(f'Invalid pixhost url - {url!r}.')


class PixHostGalleryDownloadSession(NetDriveDownloadSession):
    def __init__(self, url: str):
        NetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'pixhost_gallery_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        with TemporaryDirectory() as td:
            split = urlsplit(self.page_url)
            download_url = str(URLObject(self.page_url).
                               with_path('/'.join(['', 'gallery', split.path_segments[2], 'download'])))
            download_file(download_url, output_directory=td)
            zip_file = glob.glob(os.path.join(td, '*.zip'))[0]
            with zipfile.ZipFile(zip_file, 'r') as zf:
                zf.extractall(dst_dir)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('pixhost', 'to') and \
            tuple(split.path_segments[1:2]) == ('gallery',)


class PixHostShowDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'pixhost_show_{"_".join(split.path_segments[2:])}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        url = get_direct_url_for_pixhost(self.page_url, session=session)
        _, ext = os.path.splitext(urlsplit(url).filename.lower())
        dst_file = os.path.join(dst_dir, f'{self.resource_id}{ext}')
        download_file(url, filename=dst_file, session=session)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('pixhost', 'to') and \
            tuple(split.path_segments[1:2]) == ('show',)
