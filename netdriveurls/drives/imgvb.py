import os

from hbutils.system import urlsplit

from .base import StandaloneFileNetDriveDownloadSession
from .jpg5su import get_og_image_url
from ..utils import get_requests_session, download_file


class ImgvbImageDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        split = urlsplit(self.page_url)
        id_ = split.path_segments[2].rsplit('.', maxsplit=1)[-1]
        return f'imgvb_image_{id_}'

    def download_to_directory(self, dst_dir: str):
        session = get_requests_session()
        direct_url = get_og_image_url(self.page_url, session=session)
        _, ext = os.path.splitext(urlsplit(direct_url).filename.lower())
        filename = os.path.join(dst_dir, f'{self.resource_id}{ext}')
        download_file(direct_url, filename=filename, session=session)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('imgvb', 'com') and \
            tuple(split.path_segments[1:2]) == ('image',)
