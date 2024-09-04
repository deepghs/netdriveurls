import pytest
from hbutils.testing import simulate_entry

from netdriveurls.config.meta import __VERSION__
from netdriveurls.entry import netdriveurlscli


@pytest.mark.unittest
class TestEntryDispatch:
    def test_version(self):
        result = simulate_entry(netdriveurlscli, ['netdriveurls', '-v'])
        assert result.exitcode == 0
        assert __VERSION__ in result.stdout
