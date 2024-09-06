import hashlib
import logging
import os.path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple

import requests
from hbutils.string import plural_word
from hbutils.system import urlsplit
from tqdm import tqdm

from .base import SeparableNetDriveDownloadSession, StandaloneFileNetDriveDownloadSession, NetDriveDownloadSession, \
    ResourceDownloadError
from ..utils import get_requests_session, download_file


def get_direct_url_and_name_for_pixeldrain(url: str, session: Optional[requests.Session] = None) \
        -> Tuple[str, str, int, str]:
    split = urlsplit(url)
    assert tuple(split.host.split('.')[-2:]) == ('pixeldrain', 'com') and \
           tuple(split.path_segments[1:2]) == ('u',), f'Invalid url: {url!r}'

    id_ = split.path_segments[2]
    session = session or get_requests_session()
    resp = session.get(f'https://pixeldrain.com/api/file/{id_}/info')
    resp.raise_for_status()
    info = resp.json()
    name, size, sha256 = info['name'], info['size'], info['hash_sha256']
    return name, f'https://pixeldrain.com/api/file/{id_}?download=1', size, sha256


def get_list_info_for_pixeldrain(url: str, session: Optional[requests.Session] = None) \
        -> List[Tuple[str, str, str, int, str]]:
    split = urlsplit(url)
    assert tuple(split.host.split('.')[-2:]) == ('pixeldrain', 'com') and \
           tuple(split.path_segments[1:2]) == ('l',), f'Invalid url: {url!r}'

    id_ = split.path_segments[2]
    session = session or get_requests_session()
    resp = session.get(f'https://pixeldrain.com/api/list/{id_}')
    resp.raise_for_status()

    return [
        (info['id'], info['name'], f'https://pixeldrain.com/api/file/{info["id"]}?download=1',
         info['size'], info['hash_sha256'])
        for info in resp.json()['files']
    ]


class PixelDrainFileDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'pixeldrain_file_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        name, url, size, sha256_expected = get_direct_url_and_name_for_pixeldrain(self.page_url, session=session)
        dst_file = os.path.join(dst_dir, name)
        download_file(url, filename=dst_file, session=session)
        hash_obj = hashlib.sha256()
        with open(dst_file, 'rb') as hash_f:
            # make sure the big files will not cause OOM
            while True:
                data = hash_f.read(1 << 20)
                if not data:
                    break
                hash_obj.update(data)
        assert sha256_expected == hash_obj.hexdigest(), \
            f'SHA256 not match, {sha256_expected!r} expected, but {hash_obj.hexdigest()} found.'

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('pixeldrain', 'com') and \
            tuple(split.path_segments[1:2]) == ('u',)


class PixelDrainListDownloadSession(SeparableNetDriveDownloadSession):
    def __init__(self, url):
        SeparableNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'pixeldrain_list_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        errors = []

        all_items = get_list_info_for_pixeldrain(self.page_url, session=session)
        pg = tqdm(total=len(all_items))

        def _download_file(url, dst_file, size, sha256_expected):
            try:
                download_file(url, filename=dst_file, expected_size=size, session=session)
                hash_obj = hashlib.sha256()
                with open(dst_file, 'rb') as hash_f:
                    # make sure the big files will not cause OOM
                    while True:
                        data = hash_f.read(1 << 20)
                        if not data:
                            break
                        hash_obj.update(data)
                assert sha256_expected == hash_obj.hexdigest(), \
                    f'SHA256 not match, {sha256_expected!r} expected, but {hash_obj.hexdigest()} found.'
            except Exception as err:
                logging.exception(f'Error when downloading {url!r} to {dst_file!r} ...')
                errors.append(err)
                if os.path.exists(dst_file):
                    os.remove(dst_file)
                raise
            finally:
                pg.update()

        tp = ThreadPoolExecutor(max_workers=12)
        for id_, name, url, expected_size, expected_sha256 in all_items:
            dst_path = os.path.join(dst_dir, name)
            tp.submit(_download_file, url, dst_path, expected_size, expected_sha256)
        tp.shutdown(wait=True)

        if errors:
            raise ResourceDownloadError(f'{plural_word(len(errors), "error")} found '
                                        f'when downloading {self.page_url!r} in total.')

    def separate(self) -> List[NetDriveDownloadSession]:
        session = get_requests_session()
        return [
            PixelDrainFileDownloadSession(f'https://pixeldrain.com/u/{id_}')
            for id_, _, _, _, _ in get_list_info_for_pixeldrain(self.page_url, session=session)
        ]

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('pixeldrain', 'com') and \
            tuple(split.path_segments[1:2]) == ('l',)
