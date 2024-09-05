import logging
from typing import List, Type, Iterator

from .base import GenericResolver, URLRecognizableError, URLUnresolvableError
from .cyberdrop import CyberDropEResolver, CyberDropDirectResolver

_KNOWN_RESOLVERS: List[Type[GenericResolver]] = []


def register_resolver(net_drive_cls: Type[GenericResolver]):
    _KNOWN_RESOLVERS.append(net_drive_cls)


register_resolver(CyberDropEResolver)
register_resolver(CyberDropDirectResolver)


def _get_resolver_for_url(url: str) -> Type[GenericResolver]:
    for resolver in _KNOWN_RESOLVERS:
        if resolver.is_solvable(url):
            return resolver

    raise URLRecognizableError(f'No resolvers available for {url!r}.')


def _iter_resolve_all(url: str) -> Iterator[str]:
    queue = [url]
    exist_ids = set()
    f = 0
    while f < len(queue):
        head = queue[f]
        f += 1
        try:
            type_ = _get_resolver_for_url(head)
        except URLRecognizableError:
            yield head
        else:
            next_urls = type_.resolve_all(head)
            logging.info(f'Resolve {head!r} --> {next_urls!r} ...')
            for next_url in next_urls:
                if next_url not in exist_ids:
                    exist_ids.add(next_url)
                    queue.append(next_url)


def resolve_url_all(url: str) -> List[str]:
    return list(_iter_resolve_all(url))


def resolve_url(url: str) -> str:
    # resolve url through the redirection urls
    s = _iter_resolve_all(url)
    try:
        return next(s)
    except StopIteration:
        raise URLUnresolvableError(f'URL {url!r} unable to resolved.')
