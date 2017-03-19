Channel
=======

The Channel class is similar to the queue.Queue class from the standard
library, but with support for the receiving side detecting when all items
to be sent over the channel have been received.

This is achieved by splitting sending (`tx`) and receiving (`rx`) sides of the
channel into separate objects and allowing `tx` objects to be closed.  `rx`
objects know there are no further items to come once the channel is empty, and
all `tx` objects for the channel have been closed.

Example
-------

.. code-block:: python

    from channel import Channel
    import threading

    def sender(tx, items):
        with tx:
            for item in items:
                tx.put(item)

    channel = Channel(50)

    threads = [threading.Thread(target=sender,
                                args=(channel.tx(), range(range_start, range_end)))
               for range_start, range_end in zip(range(0,   1000, 100),
                                                 range(200, 1200, 100))]

    for thread in threads:
        thread.start()

    for item in channel.rx():
        print(item)
