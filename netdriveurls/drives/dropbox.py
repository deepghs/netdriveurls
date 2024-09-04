import os
import shutil
import zipfile
from tempfile import TemporaryDirectory

from hbutils.system import urlsplit
from urlobject import URLObject

from .base import StandaloneFileNetDriveDownloadSession, NetDriveDownloadSession
from ..utils import download_file


def _download_url(url: str, dst_dir: str):
    download_url = URLObject(url).set_query_param('dl', '1')
    target_file = download_file(download_url, output_directory=dst_dir)
    return target_file


class DropBoxFolderDownloadSession(NetDriveDownloadSession):
    def __init__(self, url: str):
        NetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        segments = list(filter(bool, urlsplit(self.page_url).path_segments))[2:]
        return '_'.join(['dropbox', 'folder', *segments])

    def download_to_directory(self, dst_dir: str):
        with TemporaryDirectory() as td:
            src_file = _download_url(self.page_url, td)
            os.makedirs(dst_dir, exist_ok=True)
            with zipfile.ZipFile(src_file, 'r') as zf:
                zf.extractall(dst_dir)

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('dropbox', 'com') and \
            tuple(split.path_segments[1:3]) == ('scl', 'fo')


class DropBoxFileDownloadSession(StandaloneFileNetDriveDownloadSession):
    def __init__(self, url: str):
        StandaloneFileNetDriveDownloadSession.__init__(self)
        self.page_url = url

    def _get_resource_id(self) -> str:
        segments = list(filter(bool, urlsplit(self.page_url).path_segments))[2:]
        return '_'.join(['dropbox', 'file', *segments])

    def download_to_directory(self, dst_dir: str):
        with TemporaryDirectory() as td:
            src_file = _download_url(self.page_url, td)
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copyfile(src_file, os.path.join(dst_dir, os.path.basename(src_file)))

    @classmethod
    def from_url(cls, url: str):
        return cls(url)

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        split = urlsplit(url)
        return tuple(split.host.split('.')[-2:]) == ('dropbox', 'com') and \
            tuple(split.path_segments[1:3]) == ('scl', 'fi')
