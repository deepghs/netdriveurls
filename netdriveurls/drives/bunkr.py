import logging
import os.path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from urllib.parse import urljoin

import requests
from hbutils.string import plural_word
from hbutils.system import urlsplit
from pyquery import PyQuery as pq
from tqdm import tqdm

from .base import ResourceInvalidError, StandaloneFileNetDriveDownloadSession, NetDriveDownloadSession, \
    ResourceDownloadError
from ..utils import get_requests_session, download_file


def get_direct_url_for_bunkr_image(url: str, session: Optional[requests.Session] = None):
    split = urlsplit(url)
    assert tuple(split.host.split('.')[-2:-1]) in {('bunkr',), ('bunkrrr',)}, f'Invalid host: {split.host!r}'
    assert tuple(split.path_segments[1:2]) == ('i',), f'Invalid path: {url!r}'

    session = session or get_requests_session()
    resp = session.get(url)
    resp.raise_for_status()

    page = pq(resp.text)
    relurl = page('.lightgallery img').attr('src')
    if relurl:
        return urljoin(resp.url, relurl)
    else:
        raise ResourceInvalidError(f'Failed to get image url from {url!r}.')


def get_direct_url_for_bunkr_video(url: str, session: Optional[requests.Session] = None):
    split = urlsplit(url)
    assert tuple(split.host.split('.')[-2:-1]) in {('bunkr',), ('bunkrrr',)}, f'Invalid host: {split.host!r}'
    assert tuple(split.path_segments[1:2]) == ('v',), f'Invalid path: {url!r}'

    session = session or get_requests_session()
    resp = session.get(url)
    resp.raise_for_status()

    page = pq(resp.text)
    relurl = page('video#player source').attr('src')
    if relurl:
        return urljoin(resp.url, relurl)
    else:
        raise ResourceInvalidError(f'Failed to get video url from {url!r}.')


def get_direct_url_for_bunkr_file(url: str, session: Optional[requests.Session] = None):
    split = urlsplit(url)
    assert tuple(split.host.split('.')[-2:-1]) in {('bunkr',), ('bunkrrr',)}, f'Invalid host: {split.host!r}'
    assert tuple(split.path_segments[1:2]) == ('d',), f'Invalid path: {url!r}'

    session = session or get_requests_session()
    resp = session.get(url)
    resp.raise_for_status()

    page = pq(resp.text)
    go_relurl = page('.mb-6 a').attr('href')
    if not go_relurl:
        raise ResourceInvalidError(f'Failed to get file url from {url!r}.')
    go_url = urljoin(resp.url, go_relurl)

    resp = session.get(go_url)
    page = pq(resp.text)
    relurl = page('.mt-3 a').attr('href')
    if not relurl:
        raise ResourceInvalidError(f'Failed to get file url from go url {go_url!r}.')
    url = urljoin(resp.url, relurl)
    return url


def get_direct_url_for_bunkr(url: str, session: Optional[requests.Session] = None):
    split = urlsplit(url)
    assert tuple(split.host.split('.')[-2:-1]) in {('bunkr',), ('bunkrrr',)}, f'Invalid host: {split.host!r}'
    sp = tuple(split.path_segments[1:2])
    if sp == ('i',):
        return get_direct_url_for_bunkr_image(url, session=session)
    elif sp == ('v',):
        return get_direct_url_for_bunkr_video(url, session=session)
    elif sp == ('d',):
        return get_direct_url_for_bunkr_file(url, session=session)
    else:
        assert False, f'Invalid path: {url!r}.'


def get_file_urls_for_bunkr_album(url: str, session: Optional[requests.Session] = None):
    split = urlsplit(url)
    assert tuple(split.host.split('.')[-2:-1]) in {('bunkr',), ('bunkrrr',)}, f'Invalid host: {split.host!r}'
    assert tuple(split.path_segments[1:2]) == ('a',), f'Invalid path: {url!r}'

    session = session or get_requests_session()
    resp = session.get(url)
    resp.raise_for_status()

    page = pq(resp.text)
    retval = []
    for item in page('.grid-images > div').items():
        if item('a').attr('href'):
            url = urljoin(resp.url, item('a').attr('href'))
            title = item('.details > p:nth-child(1)').text().strip()
            retval.append((title, url))
    return retval


class BunkrImageDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url: str):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'{split.host}_image_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        url = get_direct_url_for_bunkr_image(self.page_url, session=session)
        dst_file = os.path.join(dst_dir, urlsplit(url).filename)
        download_file(url, filename=dst_file, session=session)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:-1]) in {('bunkr',), ('bunkrrr',)} and \
            tuple(split.path_segments[1:2]) == ('i',)


class BunkrVideoDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url: str):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'{split.host}_video_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        url = get_direct_url_for_bunkr_video(self.page_url, session=session)
        dst_file = os.path.join(dst_dir, urlsplit(url).filename)
        download_file(url, filename=dst_file, session=session)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:-1]) in {('bunkr',), ('bunkrrr',)} and \
            tuple(split.path_segments[1:2]) == ('v',)


class BunkrFileDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url: str):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'{split.host}_file_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        url = get_direct_url_for_bunkr_file(self.page_url, session=session)
        dst_file = os.path.join(dst_dir, urlsplit(url).filename)
        download_file(url, filename=dst_file, session=session)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:-1]) in {('bunkr',), ('bunkrrr',)} and \
            tuple(split.path_segments[1:2]) == ('d',)


class BunkrAlbumDownloadSession(NetDriveDownloadSession):
    def __init__(self, url: str):
        NetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'{split.host}_album_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        errors = []

        all_items = get_file_urls_for_bunkr_album(self.page_url, session=session)
        pg = tqdm(total=len(all_items))

        def _download_file(file_url, fn):
            dst_file = None
            try:
                url = get_direct_url_for_bunkr(file_url, session=session)
                dst_file = os.path.join(dst_dir, fn)
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
        for title, furl in all_items:
            tp.submit(_download_file, furl, title)
        tp.shutdown(wait=True)

        if errors:
            raise ResourceDownloadError(f'{plural_word(len(errors), "error")} found '
                                        f'when downloading {self.page_url!r} in total.')

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:-1]) in {('bunkr',), ('bunkrrr',)} and \
            tuple(split.path_segments[1:2]) == ('a',)
