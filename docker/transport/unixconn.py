import requests.adapters
import socket

from docker.transport.basehttpadapter import BaseHTTPAdapter
from .. import constants

import urllib3
import urllib3.connection
from collections import OrderedDict
from requests.models import PreparedRequest
from typing import Optional, Union
from unittest.mock import MagicMock


RecentlyUsedContainer = urllib3._collections.RecentlyUsedContainer


class UnixHTTPConnection(urllib3.connection.HTTPConnection):

    def __init__(self, base_url: str, unix_socket: str, timeout: int=60) -> None:
        super().__init__(
            'localhost', timeout=timeout
        )
        self.base_url = base_url
        self.unix_socket = unix_socket
        self.timeout = timeout

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.unix_socket)
        self.sock = sock


class UnixHTTPConnectionPool(urllib3.connectionpool.HTTPConnectionPool):
    def __init__(self, base_url: str, socket_path: str, timeout: int=60, maxsize: int=10) -> None:
        super().__init__(
            'localhost', timeout=timeout, maxsize=maxsize
        )
        self.base_url = base_url
        self.socket_path = socket_path
        self.timeout = timeout

    def _new_conn(self) -> UnixHTTPConnection:
        return UnixHTTPConnection(
            self.base_url, self.socket_path, self.timeout
        )


class UnixHTTPAdapter(BaseHTTPAdapter):

    __attrs__ = requests.adapters.HTTPAdapter.__attrs__ + ['pools',
                                                           'socket_path',
                                                           'timeout',
                                                           'max_pool_size']

    def __init__(self, socket_url: str, timeout: int=60,
                 pool_connections: int=constants.DEFAULT_NUM_POOLS,
                 max_pool_size: int=constants.DEFAULT_MAX_POOL_SIZE) -> None:
        socket_path = socket_url.replace('http+unix://', '')
        if not socket_path.startswith('/'):
            socket_path = f"/{socket_path}"
        self.socket_path = socket_path
        self.timeout = timeout
        self.max_pool_size = max_pool_size
        self.pools = RecentlyUsedContainer(
            pool_connections, dispose_func=lambda p: p.close()
        )
        super().__init__()

    def get_connection(self, url: str, proxies: Optional[OrderedDict]=None) -> Union[MagicMock, UnixHTTPConnectionPool]:
        with self.pools.lock:
            pool = self.pools.get(url)
            if pool:
                return pool

            pool = UnixHTTPConnectionPool(
                url, self.socket_path, self.timeout,
                maxsize=self.max_pool_size
            )
            self.pools[url] = pool

        return pool

    def request_url(self, request: PreparedRequest, proxies: OrderedDict) -> str:
        # The select_proxy utility in requests errors out when the provided URL
        # doesn't have a hostname, like is the case when using a UNIX socket.
        # Since proxies are an irrelevant notion in the case of UNIX sockets
        # anyway, we simply return the path URL directly.
        # See also: https://github.com/docker/docker-py/issues/811
        return request.path_url
