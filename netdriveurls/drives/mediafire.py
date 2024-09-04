import logging
import os
import re

from hbutils.system import urlsplit
from pyquery import PyQuery as pq

from .base import ResourceInvalidError, StandaloneFileNetDriveDownloadSession
from ..utils import get_requests_session, download_file


class MediaFireLinkInvalidError(ResourceInvalidError):
    pass


def get_direct_url_and_filename_for_mediafire(url: str):
    origin_url = url
    sess = get_requests_session()

    while True:
        res = sess.get(url, stream=True)
        if 'Content-Disposition' in res.headers:
            logging.info(f'Download url fetched: {url!r}')
            break

        # Need to redirect with confirmation
        url = pq(res.text)('a#downloadButton').attr('href')
        if url is None:
            raise MediaFireLinkInvalidError(f"Permission denied: {origin_url!r}\n"
                                            f"Maybe you need to change permission over 'Anyone with the link'?")

    m = re.search(
        'filename="(.*)"', res.headers['Content-Disposition']
    )
    filename = m.groups()[0].encode('iso8859').decode('utf-8')
    return url, filename


class MediaFireDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, page_url: str):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = page_url

    def _get_resource_id(self) -> str:
        id_ = urlsplit(self.page_url).path_segments[2]
        return f'mediafire_{id_}'

    def download_to_directory(self, dst_dir: str):
        url, filename = get_direct_url_and_filename_for_mediafire(self.page_url)
        os.makedirs(dst_dir, exist_ok=True)
        dst_filename = os.path.join(dst_dir, filename)
        if os.path.dirname(dst_filename):
            os.makedirs(os.path.dirname(dst_filename), exist_ok=True)
        download_file(url, filename=dst_filename)
        return dst_dir

    @classmethod
    def from_url(cls, url: str) -> 'MediaFireDownloadSession':
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('mediafire', 'com') and \
            len(split.path_segments) >= 2 and split.path_segments[1] == 'file'
