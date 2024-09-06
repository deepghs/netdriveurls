import os.path
from typing import Optional, Tuple
from urllib.parse import urljoin

import requests
from hbutils.system import urlsplit
from pyquery import PyQuery as pq

from .base import ResourceInvalidError, StandaloneFileNetDriveDownloadSession
from ..utils import get_requests_session, download_file


def _get_session(session: Optional[requests.Session] = None) -> requests.Session:
    session = session or get_requests_session()
    session.cookies.update({
        'nsfw_inter': '1',
    })
    return session


def get_direct_url_for_imagebam_image(url: str, session: Optional[requests.Session] = None) -> Tuple[str, str]:
    session = _get_session(session or get_requests_session())
    resp = session.get(url)
    resp.raise_for_status()

    page = pq(resp.text)
    name = page('.content-name span.name').text().strip()
    for aitem in page('.dropdown-menu > a').items():
        if 'download' in aitem.text().lower():
            return name, urljoin(resp.url, aitem.attr('href'))

    raise ResourceInvalidError(f'No image url found for {url!r}.')


class ImageBamImageDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url: str):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'imagebam_image_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        session = _get_session()
        name, url = get_direct_url_for_imagebam_image(self.page_url, session=session)
        dst_file = os.path.join(dst_dir, name)
        download_file(url, filename=dst_file, session=session)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('imagebam', 'com') and \
            tuple(split.path_segments[1:2]) == ('image',)


class ImageBamViewDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url: str):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'imagebam_view_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        session = _get_session()
        name, url = get_direct_url_for_imagebam_image(self.page_url, session=session)
        dst_file = os.path.join(dst_dir, name)
        download_file(url, filename=dst_file, session=session)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('imagebam', 'com') and \
            tuple(split.path_segments[1:2]) == ('view',)


if __name__ == '__main__':
    from ditk import logging

    logging.try_init_root(logging.DEBUG)
    # print(get_direct_url_for_imagebam_image('http://www.imagebam.com/image/e5bd421354406108'))
    # print(get_direct_url_for_imagebam_image('https://www.imagebam.com/image/0f7e71316357051'))
    print(get_direct_url_for_imagebam_image('https://www.imagebam.com/view/MEJ5K96'))
