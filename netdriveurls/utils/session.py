from functools import lru_cache
from typing import Optional, Dict

import requests
from random_user_agent.params import SoftwareName, OperatingSystem
from random_user_agent.user_agent import UserAgent
from requests.adapters import HTTPAdapter, Retry

DEFAULT_TIMEOUT = 60  # seconds


class TimeoutHTTPAdapter(HTTPAdapter):
    """
    Custom HTTP adapter that sets a default timeout for requests.

    Inherits from `HTTPAdapter`.

    Usage:
    - Create an instance of `TimeoutHTTPAdapter` and pass it to a `requests.Session` object's `mount` method.

    Example:
    ```python
    session = requests.Session()
    adapter = TimeoutHTTPAdapter(timeout=10)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    ```

    :param timeout: The default timeout value in seconds. (default: 10)
    :type timeout: int
    """

    def __init__(self, *args, **kwargs):
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        """
        Sends a request with the provided timeout value.

        :param request: The request to send.
        :type request: PreparedRequest
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :returns: The response from the request.
        :rtype: Response
        """
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


def get_requests_session(max_retries: int = 5, timeout: int = DEFAULT_TIMEOUT, verify: bool = True,
                         headers: Optional[Dict[str, str]] = None, session: Optional[requests.Session] = None) \
        -> requests.Session:
    """
    Returns a requests Session object configured with retry and timeout settings.

    :param max_retries: The maximum number of retries. (default: 5)
    :type max_retries: int
    :param timeout: The default timeout value in seconds. (default: 10)
    :type timeout: int
    :param headers: Additional headers to be added to the session. (default: None)
    :type headers: Optional[Dict[str, str]]
    :param session: An existing requests Session object to use. If not provided, a new Session object is created. (default: None)
    :type session: Optional[requests.Session]
    :returns: The requests Session object.
    :rtype: requests.Session
    """
    session = session or requests.session()
    retries = Retry(
        total=max_retries, backoff_factor=1,
        status_forcelist=[408, 413, 429, 500, 501, 502, 503, 504, 505, 506, 507, 509, 510, 511],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
    )
    adapter = TimeoutHTTPAdapter(max_retries=retries, timeout=timeout, pool_connections=32, pool_maxsize=32)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
        "User-Agent": get_random_ua(),
        **dict(headers or {}),
    })
    if not verify:
        session.verify = False

    return session


@lru_cache()
def _ua_pool():
    software_names = [SoftwareName.CHROME.value, SoftwareName.FIREFOX.value, SoftwareName.EDGE.value]
    operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.MACOS.value]

    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=1000)
    return user_agent_rotator


def get_random_ua():
    return _ua_pool().get_random_user_agent()


@lru_cache()
def _ua_mobile_pool():
    software_names = [SoftwareName.CHROME.value, SoftwareName.FIREFOX.value, SoftwareName.SAFARI.value]
    operating_systems = [OperatingSystem.ANDROID.value, OperatingSystem.IOS.value]

    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=1000)
    return user_agent_rotator


def get_random_mobile_ua():
    return _ua_mobile_pool().get_random_user_agent()
