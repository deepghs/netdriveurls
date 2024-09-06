from typing import Optional
from urllib.parse import urljoin

import requests

from ..utils import get_requests_session


def url_redirect(url: str, session: Optional[requests.Session] = None) -> str:
    session = session or get_requests_session()
    while True:
        resp = session.head(url, allow_redirects=False)
        if resp.status_code // 100 == 3:
            url = urljoin(resp.url, resp.headers['Location'])
        else:
            resp.raise_for_status()
            return resp.url
