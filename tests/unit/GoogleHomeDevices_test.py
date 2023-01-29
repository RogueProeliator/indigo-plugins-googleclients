import pytest

from tests.unit.RPTestFramework import indigo


@pytest.fixture()
def devices(request):
    indigo.read_test_data("", read_devices=True)
    return indigo.devices


class GoogleHomeDevicesTest:

    def test_onoff_switch(self, devices):
        assert 1 == 1
