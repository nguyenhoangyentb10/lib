"""Unit test cho state machine đếm zone — không cần camera hay GPU."""
import pytest
from app.state import state
from app.zone import ZoneCounter


def make_counter() -> ZoneCounter:
    """ZoneCounter không cần PolygonZone thật cho unit test."""
    zc = ZoneCounter.__new__(ZoneCounter)
    zc._id_zone = {}
    zc._id_buffer_from = {}
    return zc


@pytest.fixture(autouse=True)
def reset_state():
    state.reset()
    yield


# ---------------------------------------------------------------------------
# Các trường hợp đếm
# ---------------------------------------------------------------------------

def test_enter_increments_count():
    """outside → buffer → inside phải tăng count lên 1."""
    zc = make_counter()
    zc.process(1, "outside")
    zc.process(1, "buffer")
    zc.process(1, "inside")
    assert state.get() == 1


def test_exit_decrements_count():
    """inside → buffer → outside phải giảm count đi 1."""
    state.increment()           # giả lập đang có 1 người trong
    zc = make_counter()
    zc.process(1, "inside")
    zc.process(1, "buffer")
    zc.process(1, "outside")
    assert state.get() == 0


def test_skip_buffer_no_count():
    """Nhảy thẳng outside→inside (không qua buffer) không được đếm."""
    zc = make_counter()
    zc.process(1, "outside")
    zc.process(1, "inside")
    assert state.get() == 0


def test_two_people_enter():
    """2 người vào độc lập, count phải là 2."""
    zc = make_counter()
    for tid in [1, 2]:
        zc.process(tid, "outside")
        zc.process(tid, "buffer")
        zc.process(tid, "inside")
    assert state.get() == 2


def test_same_zone_no_double_count():
    """Gọi process nhiều lần cùng zone không làm count thay đổi."""
    zc = make_counter()
    zc.process(1, "outside")
    zc.process(1, "buffer")
    zc.process(1, "buffer")     # gọi lại, không thay đổi
    zc.process(1, "inside")
    assert state.get() == 1


def test_enter_then_exit():
    """Vào rồi ra: net count phải về 0."""
    zc = make_counter()
    zc.process(1, "outside")
    zc.process(1, "buffer")
    zc.process(1, "inside")
    assert state.get() == 1

    zc.process(1, "buffer")
    zc.process(1, "outside")
    assert state.get() == 0


def test_disappear_inside_no_decrement():
    """Biến mất trực tiếp từ inside (không qua buffer/outside) không được giảm count."""
    zc = make_counter()
    zc.process(1, "outside")
    zc.process(1, "buffer")
    zc.process(1, "inside")
    assert state.get() == 1

    zc._cleanup(active_ids=set())  # mất track khi đang inside
    assert state.get() == 1        # count giữ nguyên


def test_none_zone_ignored_preserves_transition():
    """Gap giữa zone (current_zone=None) không phá vỡ state machine."""
    zc = make_counter()
    # Vào: outside → None (gap) → buffer → None (gap) → inside
    zc.process(1, "outside")
    zc.process(1, None)    # gap — phải bỏ qua
    zc.process(1, "buffer")
    zc.process(1, None)    # gap — phải bỏ qua
    zc.process(1, "inside")
    assert state.get() == 1

    # Ra: inside → None (gap) → buffer → None (gap) → outside
    zc.process(1, None)    # gap
    zc.process(1, "buffer")
    zc.process(1, None)    # gap
    zc.process(1, "outside")
    assert state.get() == 0


def test_count_floor_zero():
    """count không được xuống âm dù decrement nhiều lần."""
    for _ in range(5):
        state.decrement()
    assert state.get() == 0
