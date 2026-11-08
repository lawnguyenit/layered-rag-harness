import pytest


class FakeClock:
    def __init__(self, start: float = 1_700_000_000.0):
        self.t = start
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


@pytest.fixture
def clock():
    return FakeClock()
