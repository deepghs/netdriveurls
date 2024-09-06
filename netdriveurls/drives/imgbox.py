import logging
import os.path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List
from urllib.parse import urljoin

import requests
from hbutils.string import plural_word
from hbutils.system import urlsplit
from pyquery import PyQuery as pq
from tqdm import tqdm

from .base import StandaloneFileNetDriveDownloadSession, ResourceInvalidError, NetDriveDownloadSession, \
    ResourceDownloadError, SeparableNetDriveDownloadSession
from ..utils import get_requests_session, download_file


class ImgBoxResourceInvalidError(ResourceInvalidError):
    pass


def get_direct_url_for_imgbox(url: str, session: Optional[requests.Session] = None) -> str:
    session = session or get_requests_session()
    resp = session.get(url)
    resp.raise_for_status()

    page = pq(resp.text)
    relurl = page('meta[property="og:image"]').attr('content')
    if relurl:
        return urljoin(resp.url, relurl)
    else:
        raise ImgBoxResourceInvalidError(f'No image url found for {url!r}.')


def get_file_urls_for_imgbox(url: str, session: Optional[requests.Session] = None) -> List[str]:
    session = session or get_requests_session()
    resp = session.get(url)
    resp.raise_for_status()

    page = pq(resp.text)
    retval = []
    for aitem in page('#gallery-view-content > a').items():
        if aitem.attr('href'):
            retval.append(urljoin(resp.url, aitem.attr('href')))
    return retval


class ImgBoxImageDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url: str):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'imgbox_image_{split.path_segments[1]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        url = get_direct_url_for_imgbox(self.page_url, session=session)
        _, ext = os.path.splitext(urlsplit(url).filename.lower())
        dst_file = os.path.join(dst_dir, f'{self.resource_id}{ext}')
        download_file(url, filename=dst_file, session=session)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('imgbox', 'com') and \
            len(tuple(filter(bool, split.path_segments))) == 1


class ImgBoxGalleryDownloadSession(SeparableNetDriveDownloadSession):
    def __init__(self, url: str):
        SeparableNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'imgbox_gallery_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        errors = []

        all_items = get_file_urls_for_imgbox(self.page_url, session=session)
        pg = tqdm(total=len(all_items))

        def _download_file(file_url):
            dst_file = None
            try:
                url = get_direct_url_for_imgbox(file_url, session=session)
                _, ext = os.path.splitext(urlsplit(url).filename.lower())
                fid = urlsplit(file_url).path_segments[1]
                dst_file = os.path.join(dst_dir, f'{fid}{ext}')
                download_file(url, filename=dst_file, session=session)
            except Exception as err:
                logging.exception(f'Error when downloading {file_url!r} ...')
                errors.append(err)
                if dst_file and os.path.exists(dst_file):
                    os.remove(dst_file)
                raise
            finally:
                pg.update()

        tp = ThreadPoolExecutor(max_workers=12)
        for furl in all_items:
            tp.submit(_download_file, furl)
        tp.shutdown(wait=True)

        if errors:
            raise ResourceDownloadError(f'{plural_word(len(errors), "error")} found '
                                        f'when downloading {self.page_url!r} in total.')

    def separate(self) -> List['NetDriveDownloadSession']:
        session = get_requests_session()
        return [
            ImgBoxImageDownloadSession(file_url)
            for file_url in get_file_urls_for_imgbox(self.page_url, session=session)
        ]

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('imgbox', 'com') and \
            tuple(split.path_segments[1:2]) == ('g',)
