import multiprocessing as mp
import time

from livenodes.components.bridges.bridge_process import Bridge_process


class SlowPayload:
    def __init__(self, serializing):
        self.serializing = serializing

    def __reduce__(self):
        self.serializing.set()
        time.sleep(0.2)
        return bytes, (1000000,)


def send_and_close(bridge, serializing):
    bridge.put(7, SlowPayload(serializing))
    bridge.close()


def test_close_waits_for_feeder_flush():
    bridge = Bridge_process()
    serializing = mp.Event()
    sender = mp.Process(target=send_and_close, args=(bridge, serializing))
    sender.start()
    try:
        assert serializing.wait(5)
        assert not bridge.closed_event.wait(0.05)
        ctr, payload = bridge.queue.get(timeout=5)
        assert ctr == 7 and len(payload) == 1000000
        assert bridge.closed_event.wait(5)
        sender.join(5)
        assert sender.exitcode == 0
    finally:
        if sender.is_alive():
            sender.terminate()
            sender.join(5)
        bridge.queue.close()
