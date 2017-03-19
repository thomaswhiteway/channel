from collections import deque
from threading import Condition, RLock
try:
    from time import monotonic as time
except ImportError:
    from time import time


class Full(Exception):
    pass


class Empty(Exception):
    pass


class Closed(Exception):
    pass


class Channel(object):

    class Tx(object):
        def __init__(self, channel):
            self._channel = channel
            self._channel._register_tx()

        def put(self, item, block=True, timeout=None):
            self._channel._put(item, block, timeout)

        def put_noawait(self, item):
            self.put(item, False)

        def join(self):
            self._channel.join()

        def close(self):
            self._channel._tx_complete()

        def __enter__(self):
            return self

        def __exit__(self, type, value, traceback):
            self.close()

    class Rx(object):
        def __init__(self, channel):
            self._channel = channel
            self._channel._register_rx()

        def get(self, block=True, timeout=None):
            return self._channel._get(block, timeout)

        def get_noawait(self):
            return self._get(False)

        def task_done(self):
            self._channel.task_done()

        def __iter__(self):
            while True:
                try:
                    yield self.get()
                except Closed:
                    break

    def __init__(self, capacity=0):
        self._capacity = capacity
        self._queue = deque()
        self._lock = RLock()

        self._qsize = 0
        self._tx_count = 0
        self._have_rx = False
        self._pending_tasks = 0

        self._tx_cond = Condition(self._lock)
        self._rx_cond = Condition(self._lock)
        self._join_cond = Condition(self._lock)

    def qsize(self):
        with self._lock:
            return self._qsize

    def empty(self):
        with self._lock:
            return self._qsize == 0

    def full(self):
        with self._lock:
            return self._capacity != 0 and self._qsize >= self._capacity

    def _wait_for_space(self, timeout):
        if timeout is None:
            while self.full():
                self._tx_cond.wait()
        else:
            block_until = time() + timeout
            while self.full():
                remaining = block_until - time()
                if remaining < 0:
                    break
                self._tx_cond.wait(remaining)

    def _put(self, item, block=False, timeout=None):
        with self._lock:
            if self._capacity != 0:
                if block:
                    self._wait_for_space(timeout)

                if self.full():
                    raise Full()

            self._queue.append(item)
            self._qsize += 1

            self._rx_cond.notify()

    def _wait_for_item(self, timeout=None):
        if timeout is None:
            while self.empty() and self._tx_count > 0:
                self._rx_cond.wait()
        else:
            block_until = time() + timeout
            while self.empty() and self._tx_count > 0:
                remaining = block_until - time()
                if remaining < 0:
                    break
                self._rx_cond.wait(remaining)

    def _get(self, block=True, timeout=None):
        with self._lock:
            if block:
                self._wait_for_item(timeout)

            if self._qsize == 0:
                if self._tx_count > 0:
                    raise Empty()
                else:
                    raise Closed()

            value = self._queue.popleft()
            self._qsize -= 1
            self._pending_tasks += 1

            self._tx_cond.notify()

        return value

    def _task_done(self):
        with self._lock:
            if self._pending_tasks == 0:
                raise ValueError()

            self._pending_tasks -= 1
            if self._pending_tasks == 0:
                self._join_cond.notify_all()

    def join(self):
        with self._lock:
            while self._pending_tasks > 0:
                self._join_cond.wait()

    def tx(self):
        return self.Tx(self)

    def _register_tx(self):
        with self._lock:
            if self._have_rx:
                raise Exception("Can't create Tx after Rx")
            self._tx_count += 1

    def _tx_complete(self):
        with self._lock:
            self._tx_count -= 1
            self._rx_cond.notify_all()

    def rx(self):
        return self.Rx(self)

    def _register_rx(self):
        with self._lock:
            self._have_rx = True


