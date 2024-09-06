import os.path
from concurrent.futures import ThreadPoolExecutor
from pprint import pprint
from typing import Optional, List, Tuple
from urllib.parse import urljoin

import requests
from hbutils.string import plural_word
from hbutils.system import urlsplit
from pyquery import PyQuery as pq
from tqdm import tqdm

from netdriveurls.drives import NetDriveDownloadSession
from .base import ResourceInvalidError, StandaloneFileNetDriveDownloadSession, SeparableNetDriveDownloadSession, \
    ResourceDownloadError
from ..utils import get_requests_session, download_file


def get_direct_url_from_postimg_image(url: str, session: Optional[requests.Session] = None) -> str:
    session = session or get_requests_session()
    resp = session.get(url)
    resp.raise_for_status()

    page = pq(resp.text)
    relurl = page('meta[property="og:image"]').attr('content')
    if relurl:
        return urljoin(resp.url, relurl)
    else:
        raise ResourceInvalidError(f'No url found for {url!r}.')


def get_file_urls_from_postimg_gallery(url: str, session: Optional[requests.Session] = None) -> List[Tuple[str, str]]:
    session = session or get_requests_session()
    resp = session.get(url)
    resp.raise_for_status()

    page = pq(resp.text)
    retval = []
    for item in page('#thumb-list > [data-image]').items():
        id_ = item.attr('data-image')
        url = f'https://postimg.cc/{id_}'
        name = item.attr('data-name') or id_
        ext = item.attr('data-ext')
        filename = name if not ext else f'{name}.{ext}'
        retval.append((filename, url))

    return retval


class PostImgImageDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'postimg_image_{split.path_segments[1]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        url = get_direct_url_from_postimg_image(self.page_url, session=session)
        dst_file = os.path.join(dst_dir, urlsplit(url).filename)
        download_file(url, filename=dst_file, session=session)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('postimg', 'cc') and \
            tuple(split.path_segments[1:2]) != ('gallery',) and \
            len(list(filter(bool, split.path_segments))) > 0


class PostImgGalleryDownloadSession(SeparableNetDriveDownloadSession):
    def __init__(self, url):
        SeparableNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        return f'postimg_gallery_{split.path_segments[2]}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        errors = []

        all_items = get_file_urls_from_postimg_gallery(self.page_url, session=session)
        pg = tqdm(total=len(all_items))

        def _download_file(file_url, filename):
            dst_file = None
            try:
                url = get_direct_url_from_postimg_image(file_url, session=session)
                dst_file = os.path.join(dst_dir, filename)
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
        for fn, furl in all_items:
            tp.submit(_download_file, furl, fn)
        tp.shutdown(wait=True)

        if errors:
            raise ResourceDownloadError(f'{plural_word(len(errors), "error")} found '
                                        f'when downloading {self.page_url!r} in total.')

    def separate(self) -> List[NetDriveDownloadSession]:
        session = get_requests_session()
        return [
            PostImgImageDownloadSession(file_url)
            for name, file_url in get_file_urls_from_postimg_gallery(self.page_url, session=session)
        ]

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('postimg', 'cc') and \
            tuple(split.path_segments[1:2]) == ('gallery',)


if __name__ == '__main__':
    from ditk import logging

    logging.try_init_root(logging.DEBUG)
    pprint(get_file_urls_from_postimg_gallery('https://postimg.cc/gallery/xkCyy22'))
