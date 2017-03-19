from channel import Channel, Empty, Closed, Full
import pytest


def test_send_receive():
    channel = Channel()
    tx = channel.tx()
    rx = channel.rx()

    tx.put(1)
    assert rx.get() == 1


def test_double_receive():
    channel = Channel()
    tx = channel.tx()
    rx = [channel.rx() for _ in range(2)]

    tx.put(1)
    tx.put(2)

    assert rx[0].get() == 1
    assert rx[1].get() == 2


def test_always_empty():
    channel = Channel()

    tx = channel.tx()
    rx = channel.rx()

    with pytest.raises(Empty):
        rx.get(block=False)


def test_becomes_empty():
    channel = Channel()

    tx = channel.tx()
    rx = channel.rx()

    tx.put(1)
    assert rx.get() == 1
    with pytest.raises(Empty):
        rx.get(block=False)


def test_closed():
    channel = Channel()

    tx = channel.tx()
    rx = channel.rx()

    with pytest.raises(Empty):
        rx.get(block=False)

    tx.close()

    with pytest.raises(Closed):
        rx.get(block=False)


def test_full():
    channel = Channel(1)

    tx = channel.tx()

    tx.put(10)
    with pytest.raises(Full):
        tx.put(11, block=False)

