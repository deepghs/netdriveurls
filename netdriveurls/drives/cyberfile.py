import os.path
import re
from pprint import pprint
from typing import Optional

import requests
from hbutils.system import urlsplit
from pyquery import PyQuery as pq

from .base import ResourceInvalidError, StandaloneFileNetDriveDownloadSession
from ..utils import get_requests_session, download_file


def get_all_direct_urls_for_cyberfile_file(url: str, session: Optional[requests.Session] = None):
    session = session or get_requests_session()
    resp = session.get(url)
    resp.raise_for_status()

    num_id_texts = re.findall(r'showFileInformation\(\s*(?P<num_id>\d+)\s*\)', resp.text)
    if not num_id_texts:
        raise ResourceInvalidError(f'No resource id found for {url!r}.')
    num_id = int(num_id_texts[0])

    resp = session.post('https://cyberfile.me/account/ajax/file_details', data={'u': str(num_id)})
    resp.raise_for_status()
    finfo = resp.json()
    filename = finfo['page_title']

    with open('test_su2.html', 'w') as f:
        print(finfo['html'], file=f)

    download_items = []
    page = pq(finfo['html'])
    for bitem in page('button[onClick]').items():
        if 'openUrl' in bitem.attr('onclick') and 'download' in bitem.text().lower().strip():
            onclick_code = bitem.attr('onclick')
            url = eval(re.findall(r'openUrl\(\s*(?P<url>[\s\S]+?)\s*?\)\s*;', onclick_code)[0])
            download_items.append({'label': None, 'url': url})

    for aitem in page('ul.dropdown-info li a[onClick]').items():
        onclick_code = aitem.attr('onclick')
        label = aitem.text().strip()
        url = eval(re.findall(r'openUrl\(\s*(?P<url>[\s\S]+?)\s*?\)\s*;', onclick_code)[0])
        download_items.append({'label': label, 'url': url})

    return filename, download_items


def get_direct_url_for_cyberfile_file(url: str, session: Optional[requests.Session] = None):
    filename, download_items = get_all_direct_urls_for_cyberfile_file(url, session=session)
    if not download_items:
        raise ResourceInvalidError(f'No download urls found in {url!r}.')
    return filename, download_items[0]['url']


class CyberFileDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'cyberfile_file_{split.path_segments[1]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        filename, url = get_direct_url_for_cyberfile_file(self.page_url, session=session)
        download_file(url, filename=os.path.join(dst_dir, filename), session=session)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('cyberfile', 'me') and \
            tuple(split.path_segments[1:2]) not in {('folder',), ('share',)} and \
            len(split.path_segments) >= 2


if __name__ == '__main__':
    from ditk import logging

    logging.try_init_root(logging.DEBUG)
    # pprint(get_direct_url_for_cyberfile_file('https://cyberfile.me/zZzY'))
    # pprint(get_direct_url_for_cyberfile_file('https://cyberfile.me/wMa1'))
    # pprint(get_direct_url_for_cyberfile_file('https://cyberfile.me/wbI3'))
    pprint(get_direct_url_for_cyberfile_file('https://cyberfile.me/rt8Q'))
