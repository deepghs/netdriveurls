import os
import sys
from contextlib import contextmanager

import pyrfc6266
import requests
from tqdm.auto import tqdm

from .session import get_requests_session


class _FakeClass:
    def update(self, *args, **kwargs):
        pass


@contextmanager
def _with_tqdm(expected_size, desc, silent: bool = False):
    with open(os.devnull, 'w') as of_:
        with tqdm(total=expected_size, unit='B', unit_scale=True,
                  unit_divisor=1024, file=of_ if silent else sys.stderr, desc=desc) as pbar:
            yield pbar


def download_file(url, filename=None, output_directory=None,
                  expected_size: int = None, desc=None, session=None, silent: bool = False,
                  **kwargs):
    session = session or get_requests_session()
    response = session.get(url, stream=True, allow_redirects=True, **kwargs)
    expected_size = expected_size or response.headers.get('Content-Length', None)
    if filename is None:
        filename = pyrfc6266.parse_filename(response.headers.get('Content-Disposition'))
    if output_directory is not None:
        filename = os.path.join(output_directory, filename)
    expected_size = int(expected_size) if expected_size is not None else expected_size

    desc = desc or os.path.basename(filename)
    directory = os.path.dirname(filename)
    if directory:
        os.makedirs(directory, exist_ok=True)

    try:
        with open(filename, 'wb') as f:
            with _with_tqdm(expected_size, desc, silent) as pbar:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
                    pbar.update(len(chunk))

        actual_size = os.path.getsize(filename)
        if expected_size is not None and actual_size != expected_size:
            raise requests.exceptions.HTTPError(f"Downloaded file is not of expected size, "
                                                f"{expected_size} expected but {actual_size} found.")
    except BaseException:
        # os.remove(filename)
        raise

    return filename
