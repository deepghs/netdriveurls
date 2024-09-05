from typing import List


class GenericResolver:
    @classmethod
    def resolve_all(cls, url: str) -> List[str]:
        raise NotImplementedError

    @classmethod
    def is_solvable(cls, url: str) -> bool:
        raise NotImplementedError


class URLUnresolvableError(Exception):
    pass


class URLRecognizableError(Exception):
    pass


class StandaloneResolver(GenericResolver):
    @classmethod
    def resolve_all(cls, url: str) -> List[str]:
        try:
            return [cls.resolve(url)]
        except URLUnresolvableError:
            return []

    @classmethod
    def resolve(cls, url: str) -> str:
        # raise URLUnresolvableError when unable to resolve
        raise NotImplementedError

    @classmethod
    def is_solvable(cls, url: str) -> bool:
        raise NotImplementedError
