import unittest
import docker
import pytest
from docker.constants import DEFAULT_UNIX_SOCKET
from docker.constants import DEFAULT_NPIPE
from docker.constants import IS_WINDOWS_PLATFORM
from docker.context import ContextAPI, Context


class BaseContextTest(unittest.TestCase):
    @pytest.mark.skipif(
        IS_WINDOWS_PLATFORM, reason='Linux specific path check'
    )
    def test_url_compatibility_on_linux(self) -> None:
        c = Context("test")
        assert c.Host == DEFAULT_UNIX_SOCKET[5:]

    @pytest.mark.skipif(
        not IS_WINDOWS_PLATFORM, reason='Windows specific path check'
    )
    def test_url_compatibility_on_windows(self) -> None:
        c = Context("test")
        assert c.Host == DEFAULT_NPIPE

    def test_fail_on_default_context_create(self) -> None:
        with pytest.raises(docker.errors.ContextException):
            ContextAPI.create_context("default")

    def test_default_in_context_list(self) -> None:
        found = False
        ctx = ContextAPI.contexts()
        for c in ctx:
            if c.Name == "default":
                found = True
        assert found is True

    def test_get_current_context(self) -> None:
        assert ContextAPI.get_current_context().Name == "default"

    def test_https_host(self) -> None:
        c = Context("test", host="tcp://testdomain:8080", tls=True)
        assert c.Host == "https://testdomain:8080"

    def test_context_inspect_without_params(self) -> None:
        ctx = ContextAPI.inspect_context()
        assert ctx["Name"] == "default"
        assert ctx["Metadata"]["StackOrchestrator"] == "swarm"
        assert ctx["Endpoints"]["docker"]["Host"] in (
            DEFAULT_NPIPE,
            DEFAULT_UNIX_SOCKET[5:],
        )
