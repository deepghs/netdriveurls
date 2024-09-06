import os
import shutil
from typing import List

from hbutils.system import TemporaryDirectory


class ResourceInvalidError(Exception):
    pass


class ResourceUnrecognizableError(Exception):
    pass


class ResourceConstraintError(Exception):
    pass


class ResourceDownloadError(Exception):
    pass


class NetDriveDownloadSession:
    def __init__(self):
        self._resource_id = None

    @property
    def resource_id(self) -> str:
        if self._resource_id is None:
            self._resource_id = self._get_resource_id()
        return self._resource_id

    def _get_resource_id(self) -> str:
        raise NotImplementedError  # pragma: no cover

    def download_to_directory(self, dst_dir: str):
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def from_url(cls, url: str):
        # in this method, url is guaranteed to be a valid url of this site
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        raise NotImplementedError  # pragma: no cover

    def __repr__(self):
        return f'<{self.__class__.__name__} id: {self.resource_id!r}>'


class StandaloneFileNetDriveDownloadSession(NetDriveDownloadSession):
    def _get_resource_id(self) -> str:
        raise NotImplementedError  # pragma: no cover

    def download_to_file(self, dst_file: str):
        with TemporaryDirectory() as td:
            self.download_to_directory(dst_dir=td)
            files = os.listdir(td)
            if len(files) == 1:
                if os.path.dirname(dst_file):
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                src_file = os.path.join(td, files[0])
                shutil.copyfile(src_file, dst_file)
            else:
                raise ResourceConstraintError(f'Only 1 file expected, '
                                              f'but {files!r} found in downloaded directory of {self!r}.')

    def download_to_directory(self, dst_dir: str):
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def from_url(cls, url: str):
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        raise NotImplementedError  # pragma: no cover


class SeparableNetDriveDownloadSession(NetDriveDownloadSession):
    def _get_resource_id(self) -> str:
        raise NotImplementedError  # pragma: no cover

    def download_to_directory(self, dst_dir: str):
        raise NotImplementedError  # pragma: no cover

    def separate(self) -> List['NetDriveDownloadSession']:
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def from_url(cls, url: str):
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        raise NotImplementedError  # pragma: no cover
