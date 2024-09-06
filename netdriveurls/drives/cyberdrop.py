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


def get_file_links_for_cyberdrop(url: str, session: Optional[requests.Session] = None):
    split = urlsplit(url)
    assert tuple(split.host.split('.')) == ('cyberdrop', 'me'), f'Invalid host: {split.host!r}'
    assert tuple(split.path_segments[1:2]) == ('a',), f'Invalid path: {url!r}'

    session = session or get_requests_session()
    resp = session.get(url)
    resp.raise_for_status()

    retval = []
    for item in pq(resp.text)('#table > *').items():
        a = item('a#file')
        file_page_url = urljoin(resp.url, a.attr('href'))
        title = a.attr('title')
        retval.append((title, file_page_url))

    return retval


def get_direct_file_link_for_cyberdrop(url: str, session: Optional[requests.Session] = None):
    split = urlsplit(url)
    assert tuple(split.host.split('.')) == ('cyberdrop', 'me'), f'Invalid host: {split.host!r}'
    assert tuple(split.path_segments[1:2]) == ('f',), f'Invalid path: {url!r}'

    file_id = split.path_segments[2]
    session = session or get_requests_session()
    resp = session.get(f'https://api.cyberdrop.me/api/file/info/{file_id}')
    resp.raise_for_status()
    file_info = resp.json()

    resp = session.get(file_info['auth_url'])
    resp.raise_for_status()
    return resp.json()['url'], file_info['name'], file_info['size']


class CyberDropFileDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'cyberdrop_file_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        url, name, size = get_direct_file_link_for_cyberdrop(self.page_url, session=session)
        os.makedirs(dst_dir, exist_ok=True)
        download_file(url, filename=os.path.join(dst_dir, name), expected_size=size)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')) == ('cyberdrop', 'me') and \
            tuple(split.path_segments[1:2]) == ('f',)


class CyberDropArchiveDownloadSession(SeparableNetDriveDownloadSession):
    def __init__(self, url):
        NetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'cyberdrop_folder_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        os.makedirs(dst_dir, exist_ok=True)
        errors = []

        all_items = get_file_links_for_cyberdrop(self.page_url, session=session)
        pg = tqdm(total=len(all_items))

        def _download_file(furl, dst_file):
            try:
                url, name, size = get_direct_file_link_for_cyberdrop(furl, session=session)
                download_file(url, filename=dst_file, expected_size=size)
            except Exception as err:
                logging.exception(f'Error when downloading {furl!r} to {dst_file!r} ...')
                errors.append(err)
                if os.path.exists(dst_file):
                    os.remove(dst_file)
                raise
            finally:
                pg.update()

        tp = ThreadPoolExecutor(max_workers=12)
        for rname, file_url in all_items:
            tp.submit(_download_file, file_url, os.path.join(dst_dir, rname))
        tp.shutdown(wait=True)

        if errors:
            raise ResourceDownloadError(f'{plural_word(len(errors), "error")} found '
                                        f'when downloading {self.page_url!r} in total.')

    def separate(self) -> List[NetDriveDownloadSession]:
        session = get_requests_session()
        return [
            CyberDropFileDownloadSession(file_url)
            for _, file_url in get_file_links_for_cyberdrop(self.page_url, session=session)
        ]

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')) == ('cyberdrop', 'me') and \
            tuple(split.path_segments[1:2]) == ('a',)
