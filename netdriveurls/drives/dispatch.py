from typing import Type, List, Union

from .base import NetDriveDownloadSession, ResourceInvalidError, StandaloneFileNetDriveDownloadSession
from .dropbox import DropBoxFileDownloadSession, DropBoxFolderDownloadSession
from .gofile import GoFileFolderDownloadSession
from .mediafire import MediaFireDownloadSession
from ..resolve import resolve_url

_KNOWN_SESSIONS: List[Type[NetDriveDownloadSession]] = []


def register_net_drive(net_drive_cls: Type[NetDriveDownloadSession]):
    _KNOWN_SESSIONS.append(net_drive_cls)


register_net_drive(MediaFireDownloadSession)
register_net_drive(DropBoxFolderDownloadSession)
register_net_drive(DropBoxFileDownloadSession)
register_net_drive(GoFileFolderDownloadSession)


def from_url(url: str) -> Union[NetDriveDownloadSession, StandaloneFileNetDriveDownloadSession]:
    origin_url, url = url, resolve_url(url)
    for net_drive_cls in _KNOWN_SESSIONS:
        if net_drive_cls.is_valid_url(url):
            return net_drive_cls.from_url(url)

    raise ResourceInvalidError(f'Unable to determine the net drive type of {url!r} '
                               f'(resolved from {origin_url}).')
