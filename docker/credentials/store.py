import errno
import json
import shutil
import subprocess
import warnings

from . import constants
from . import errors
from .utils import create_environment_dict
from typing import Any, Dict, Optional


class Store:
    def __init__(self, program: str, environment: None=None) -> None:
        """ Create a store object that acts as an interface to
            perform the basic operations for storing, retrieving
            and erasing credentials using `program`.
        """
        self.program = constants.PROGRAM_PREFIX + program
        self.exe = shutil.which(self.program)
        self.environment = environment
        if self.exe is None:
            warnings.warn(
                f'{self.program} not installed or not available in PATH',
                stacklevel=1,
            )

    def get(self, server: str):
        """ Retrieve credentials for `server`. If no credentials are found,
            a `StoreError` will be raised.
        """
        if not isinstance(server, bytes):
            server = server.encode('utf-8')
        data = self._execute('get', server)
        result = json.loads(data.decode('utf-8'))

        # docker-credential-pass will return an object for inexistent servers
        # whereas other helpers will exit with returncode != 0. For
        # consistency, if no significant data is returned,
        # raise CredentialsNotFound
        if result['Username'] == '' and result['Secret'] == '':
            raise errors.CredentialsNotFound(
                f'No matching credentials in {self.program}'
            )

        return result

    def store(self, server, username, secret):
        """ Store credentials for `server`. Raises a `StoreError` if an error
            occurs.
        """
        data_input = json.dumps({
            'ServerURL': server,
            'Username': username,
            'Secret': secret
        }).encode('utf-8')
        return self._execute('store', data_input)

    def erase(self, server) -> None:
        """ Erase credentials for `server`. Raises a `StoreError` if an error
            occurs.
        """
        if not isinstance(server, bytes):
            server = server.encode('utf-8')
        self._execute('erase', server)

    def list(self) -> Dict[Any, Any]:
        """ List stored credentials. Requires v0.4.0+ of the helper.
        """
        data = self._execute('list', None)
        return json.loads(data.decode('utf-8'))

    def _execute(self, subcmd: str, data_input: Optional[bytes]) -> bytes:
        if self.exe is None:
            raise errors.StoreError(
                f'{self.program} not installed or not available in PATH'
            )
        output = None
        env = create_environment_dict(self.environment)
        try:
            output = subprocess.check_output(
                [self.exe, subcmd], input=data_input, env=env,
            )
        except subprocess.CalledProcessError as e:
            raise errors.process_store_error(e, self.program) from e
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise errors.StoreError(
                    f'{self.program} not installed or not available in PATH'
                ) from e
            else:
                raise errors.StoreError(
                    f'Unexpected OS error "{e.strerror}", errno={e.errno}'
                ) from e
        return output
