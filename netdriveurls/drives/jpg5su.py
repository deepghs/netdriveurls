import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List
from urllib.parse import urljoin

import requests
from hbutils.string import plural_word
from hbutils.system import urlsplit
from pyquery import PyQuery as pq
from tqdm import tqdm

from .base import StandaloneFileNetDriveDownloadSession, NetDriveDownloadSession, ResourceDownloadError, \
    SeparableNetDriveDownloadSession
from ..utils import get_requests_session, download_file


def get_og_image_url(url: str, session: Optional[requests.Session] = None):
    session = session or get_requests_session()
    resp = session.get(url)
    resp.raise_for_status()

    page = pq(resp.text)
    url = urljoin(resp.url, page('[property="og:image"]').attr('content'))
    return url


def get_direct_url_for_jpg5su(url: str, session: Optional[requests.Session] = None):
    split = urlsplit(url)
    assert tuple(split.host.split('.')[-2:]) in {('jpg5', 'su'), ('jpg4', 'su')}, f'Invalid host: {split.host!r}'
    assert tuple(split.path_segments[1:2]) == ('img',), f'Invalid path: {url!r}'

    return get_og_image_url(url, session=session)


def get_file_urls_for_jpg5su(url: str, session: Optional[requests.Session] = None):
    split = urlsplit(url)
    assert tuple(split.host.split('.')[-2:]) in {('jpg5', 'su'), ('jpg4', 'su')}, f'Invalid host: {split.host!r}'
    assert tuple(split.path_segments[1:2]) == ('a',), f'Invalid path: {url!r}'

    session = session or get_requests_session()
    next_url = url
    retval = []
    while True:
        resp = session.get(next_url)
        resp.raise_for_status()
        page = pq(resp.text)
        for item in page('.pad-content-listing > .list-item').items():
            a = item('.list-item-desc-title > a')
            title = a.text().strip()
            url = urljoin(resp.url, a.attr('href'))
            retval.append((title, url))

        if page('a[data-pagination="next"]').attr('href'):
            next_url = urljoin(resp.url, page('a[data-pagination="next"]').attr('href'))
        else:
            break

    return retval


class JPG5SuFileDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        id_ = split.path_segments[2].rsplit('.', maxsplit=1)[-1]
        return f'jpg5su_image_{id_}'

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
        return tuple(split.host.split('.')[-2:]) in {('jpg5', 'su'), ('jpg4', 'su')} and \
            tuple(split.path_segments[1:2]) == ('img',)


class JPG5SuAlbumDownloadSession(SeparableNetDriveDownloadSession):
    def __init__(self, url):
        SeparableNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        id_ = split.path_segments[2].rsplit('.', maxsplit=1)[-1]
        return f'jpg5su_album_{id_}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        errors = []

        all_items = get_file_urls_for_jpg5su(self.page_url, session=session)
        pg = tqdm(total=len(all_items))

        def _download_file(file_url, title):
            dst_file = None
            try:
                url = get_direct_url_for_jpg5su(file_url, session=session)
                _, ext = os.path.splitext(urlsplit(url).filename.lower())
                dst_file = os.path.join(dst_dir, f'{title}{ext}')
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

    def separate(self) -> List[NetDriveDownloadSession]:
        session = get_requests_session()
        return [
            JPG5SuFileDownloadSession(file_url)
            for _, file_url in get_file_urls_for_jpg5su(self.page_url, session=session)
        ]

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) in {('jpg5', 'su'), ('jpg4', 'su')} and \
            tuple(split.path_segments[1:2]) == ('a',)
