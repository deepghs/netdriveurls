from typing import Type, List, Union

from .base import NetDriveDownloadSession, ResourceInvalidError, SeparableNetDriveDownloadSession
from .bunkr import BunkrImageDownloadSession, BunkrAlbumDownloadSession, BunkrVideoDownloadSession, \
    BunkrFileDownloadSession
from .cyberdrop import CyberDropArchiveDownloadSession, CyberDropFileDownloadSession
from .dropbox import DropBoxFileDownloadSession, DropBoxFolderDownloadSession
from .gofile import GoFileFolderDownloadSession
from .ibb import IbbFileDownloadSession
from .imagebam import ImageBamViewDownloadSession, ImageBamImageDownloadSession
from .imgbox import ImgBoxImageDownloadSession, ImgBoxGalleryDownloadSession
from .jpg5su import JPG5SuFileDownloadSession, JPG5SuAlbumDownloadSession
from .mediafire import MediaFireDownloadSession
from .pixeldrain import PixelDrainListDownloadSession, PixelDrainFileDownloadSession
from .pixhost import PixHostShowDownloadSession, PixHostGalleryDownloadSession
from .saint2 import Saint2EmbedDownloadSession
from ..resolve import resolve_url

_KNOWN_SESSIONS: List[Type[NetDriveDownloadSession]] = []


def register_net_drive(net_drive_cls: Type[NetDriveDownloadSession]):
    _KNOWN_SESSIONS.append(net_drive_cls)


register_net_drive(MediaFireDownloadSession)
register_net_drive(DropBoxFolderDownloadSession)
register_net_drive(DropBoxFileDownloadSession)
register_net_drive(GoFileFolderDownloadSession)
register_net_drive(CyberDropFileDownloadSession)
register_net_drive(CyberDropArchiveDownloadSession)
register_net_drive(JPG5SuFileDownloadSession)
register_net_drive(JPG5SuAlbumDownloadSession)
register_net_drive(IbbFileDownloadSession)
register_net_drive(Saint2EmbedDownloadSession)
register_net_drive(BunkrImageDownloadSession)
register_net_drive(BunkrAlbumDownloadSession)
register_net_drive(BunkrVideoDownloadSession)
register_net_drive(BunkrFileDownloadSession)
register_net_drive(PixHostGalleryDownloadSession)
register_net_drive(PixHostShowDownloadSession)
register_net_drive(ImgBoxImageDownloadSession)
register_net_drive(ImgBoxGalleryDownloadSession)
register_net_drive(PixelDrainFileDownloadSession)
register_net_drive(PixelDrainListDownloadSession)
register_net_drive(ImageBamImageDownloadSession)
register_net_drive(ImageBamViewDownloadSession)


def from_url(url: str) -> Union[NetDriveDownloadSession, SeparableNetDriveDownloadSession]:
    origin_url, url = url, resolve_url(url)
    for net_drive_cls in _KNOWN_SESSIONS:
        if net_drive_cls.is_valid_url(url):
            return net_drive_cls.from_url(url)

    raise ResourceInvalidError(f'Unable to determine the net drive type of {url!r} '
                               f'(resolved from {origin_url}).')


def sep_from_url(url: str) -> List[Union[NetDriveDownloadSession]]:
    obj = from_url(url)
    queue = [obj]
    result = []
    f = 0
    while f < len(queue):
        head = queue[f]
        f += 1
        if isinstance(head, SeparableNetDriveDownloadSession):
            queue.extend(head.separate())
        else:
            result.append(head)
    return result
