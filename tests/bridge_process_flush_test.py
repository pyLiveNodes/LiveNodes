import asyncio
import multiprocessing as mp
import time

from livenodes.components.bridges.bridge_process import Bridge_process

PAYLOAD = 1_000_000


class SlowPayload:
    """Pickles slowly, so the item is still in the sender's feeder thread when close() returns."""

    def __init__(self, serializing):
        self.serializing = serializing

    def __reduce__(self):
        self.serializing.set()
        time.sleep(0.2)
        return bytes, (b"x" * PAYLOAD,)   # a real 1 MB pickled body, not one built on unpickling


def send_and_close(bridge, items, serializing=None):
    for ctr, item in enumerate(items):
        bridge.put(ctr, SlowPayload(serializing) if item is None else item)
    bridge.close()


async def receive_all(bridge, timeout=10):
    """Receiver loop through the bridge API, like a node: read until closed_and_empty()."""
    got = {}

    async def reader():
        while True:
            ctr = await bridge.update()
            if ctr is None:   # end of stream: nothing follows
                continue
            found, value = bridge.get(ctr)
            assert found
            got[ctr] = value
            bridge.discard_before(ctr)

    task = asyncio.ensure_future(reader())
    deadline = time.monotonic() + timeout
    while not bridge.closed_and_empty():
        assert time.monotonic() < deadline, "receiver never saw the end of stream"
        assert not task.done(), task.exception()
        await asyncio.sleep(0.005)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    return got


def test_receiver_gets_slow_item_before_end_of_stream():
    bridge = Bridge_process()
    serializing = mp.Event()
    sender = mp.Process(target=send_and_close, args=(bridge, [None], serializing))
    sender.start()
    try:
        assert serializing.wait(5)
        got = asyncio.run(receive_all(bridge))
        assert list(got) == [0] and got[0] == b"x" * PAYLOAD
        sender.join(5)
        assert sender.exitcode == 0
    finally:
        if sender.is_alive():
            sender.terminate()
            sender.join(5)


def test_many_large_items_all_arrive():
    bridge = Bridge_process()
    items = [bytes([i]) * PAYLOAD for i in range(20)]   # far more than a pipe buffer holds
    sender = mp.Process(target=send_and_close, args=(bridge, items))
    sender.start()
    try:
        got = asyncio.run(receive_all(bridge))
        assert sorted(got) == list(range(20))
        assert all(got[i] == items[i] for i in range(20))
        sender.join(5)
        assert sender.exitcode == 0
    finally:
        if sender.is_alive():
            sender.terminate()
            sender.join(5)


def test_close_does_not_block_without_a_reader():
    bridge = Bridge_process()
    bridge.put(0, b"x" * PAYLOAD)
    t = time.monotonic()
    bridge.close()
    bridge.close()   # idempotent
    assert time.monotonic() - t < 1.0
    bridge.queue.cancel_join_thread()   # nobody reads in this test: don't wait for the feeder at exit
