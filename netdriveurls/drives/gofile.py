import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from hashlib import md5
from typing import Optional, Dict, Tuple, List

import requests
from hbutils.string import plural_word
from hbutils.system import urlsplit

from .base import NetDriveDownloadSession, ResourceDownloadError
from ..utils import get_requests_session, download_file


@lru_cache()
def _get_guest_profile_raw(magic):
    _ = magic
    session = get_requests_session()
    resp = session.post('https://api.gofile.io/accounts')
    resp.raise_for_status()
    return resp.json()


@lru_cache()
def _get_guest_profile():
    # timeout: 60 * 60
    return _get_guest_profile_raw(int(time.time() // (60 * 60)))


def _get_guest_token():
    return _get_guest_profile()['data']['token']


@lru_cache()
def _get_wd_code():
    session = get_requests_session()
    resp = session.get('https://gofile.io/dist/js/alljs.js')
    resp.raise_for_status()
    raw_token = re.findall(r'\{\s*wt\s*:\s*(\S+?)\s*}', resp.text)[0]
    return json.loads(raw_token)


def _extract_files(data) -> List[Tuple[Tuple[str, ...], str, int, str]]:
    _id_to_node: Dict[str, dict] = {}

    def _node_checkin(d):
        _id_to_node[d['id']] = d
        if d['type'] == 'folder':
            for child in d['children'].values():
                _node_checkin(child)

    _node_checkin(data)

    _id_to_segs: Dict[str, Tuple[str, ...]] = {}

    def _get_node_segs(id_: str):
        if id_ in _id_to_segs:
            return _id_to_segs[id_]

        node_info = _id_to_node[id_]
        if node_info.get('parentFolder'):
            segs = (*_get_node_segs(node_info['parentFolder']), node_info['name'])
        else:
            if node_info['type'] == 'file':
                segs = (node_info['name'],)
            else:
                segs = ()
        _id_to_segs[id_] = segs
        return segs

    retval = []
    for node in _id_to_node.values():
        if node['type'] == 'file':
            retval.append((_get_node_segs(node['id']), node['link'], node['size'], node['md5']))
    retval = sorted(retval)
    return retval


def get_direct_urls_for_gofile_folder(
        url: str, token: Optional[str] = None,
        session: Optional[requests.Session] = None
) -> List[Tuple[Tuple[str, ...], str, int, str]]:
    session = session or get_requests_session()

    split = urlsplit(url)
    assert tuple(split.host.split('.')[-2:]) == ('gofile', 'io'), f'Unexpected host: {split.host!r}'
    assert tuple(split.path_segments[1:2]) == ('d',), f'Invalid url: {url!r}'
    resource_id = split.path_segments[2]

    token = token or _get_guest_token()
    resp = session.get(
        f'https://api.gofile.io/contents/{resource_id}',
        params={'wt': _get_wd_code()},
        headers={'Authorization': f'Bearer {token}'}
    )
    resp.raise_for_status()

    return _extract_files(resp.json()['data'])


class GoFileFolderDownloadSession(NetDriveDownloadSession):
    def __init__(self, url: str):
        NetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        return f'gofile_folder_{urlsplit(self.page_url).path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        os.makedirs(dst_dir, exist_ok=True)
        token = _get_guest_token()
        session = get_requests_session()
        errors = []

        def _download_file(url, dst_file, size, md5_expected):
            try:
                download_file(url, filename=dst_file, expected_size=size,
                              cookies={'accountToken': token}, session=session)
                hash_obj = md5()
                with open(dst_file, 'rb') as hash_f:
                    # make sure the big files will not cause OOM
                    while True:
                        data = hash_f.read(1 << 20)
                        if not data:
                            break
                        hash_obj.update(data)
                assert md5_expected == hash_obj.hexdigest(), \
                    f'MD5 not match, {md5_expected!r} expected, but {hash_obj.hexdigest()} found.'
            except Exception as err:
                logging.exception(f'Error when downloading {url!r} to {dst_file!r} ...')
                errors.append(err)
                raise

        tp = ThreadPoolExecutor(max_workers=12)
        for segs, url, expected_size, expected_md5 in \
                get_direct_urls_for_gofile_folder(self.page_url, token=token, session=session):
            dst_path = os.path.join(dst_dir, *segs)
            tp.submit(_download_file, url, dst_path, expected_size, expected_md5)
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
        return tuple(split.host.split('.')[-2:]) == ('gofile', 'io') and \
            tuple(split.path_segments[1:2]) == ('d',)
