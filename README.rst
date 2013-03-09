libtask9
========

This is a fairly straightforward port of Russ Cox' libthread C library
from Plan 9 from User Space (aka plan9port_) to CPython. It depends on
the greenlet module.

Procs
  Operating system threads created by the Python threading module.

Tasks
  User-space scheduled coroutines (libthread calls them threads, I've
  renamed them to tasks to avoid confusion with the Python threading module)
  implemented using the greenlet module.

  They are cooperatively switched by their respective Proc and are
  bound only to that Proc's execution thread.

Channels
  A scheduling and synchronization mechanism, used to coordinate tasks
  in the same Proc or among different Procs.

plan9port_ libthread Documentation
----------------------------------
- thread_
- ioproc_

.. _plan9port: http://swtch.com/plan9port
.. _thread: http://swtch.com/plan9port/man/man3/thread.html
.. _ioproc: http://swtch.com/plan9port/man/man3/ioproc.html

Example
-------
::

    import sys
    import socket
    from functools import partial
    from libtask9 import new_task, curtask, IOProc, sleep, Channel, alt, alt_recv, after
    
    def ticker():
        while True:
            print 'tick from {}'.format(curtask())
            sleep(2)
    
    class Acceptor(object):
        def __init__(self):
            self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            self._s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._s.bind(('0.0.0.0', 8080))
            self._s.listen(1)
    
        def __call__(self):
            try:
                return self._s.accept()
            except socket.error:
                return None, None
    
        def close_listener(self):
            self._s.shutdown(socket.SHUT_RDWR)
            self._s.close()
    
    def iotest(args):
        io = IOProc('io1')
        io.start()
        new_task(ticker)
    
        def accept_task(acceptor, reply_chan):
            client, addr = io.iocall(acceptor)
            print 'got a connection from: {}'.format(addr)
            reply_chan.send(client)
    
        print 'waiting 10 seconds for io to complete'
        client_ch = Channel(1)
        acceptor = Acceptor()
        new_task(accept_task, acceptor, client_ch)
    
        idx, result = alt(
            alt_recv(client_ch),
            alt_recv(after(10)),
            canblock=True
        )
    
        if idx == 0:
            client = result
            io.iocall(partial(client.send, 'hello!\n'))
            io.iocall(client.close)
        elif idx == 1:
            print 'timeout, forcing close on listener'
            acceptor.close_listener()
            # allow the iocall a chance to complete before we call io.stop()
            client_ch.recv()
    
        io.stop()
    
    def main(args):
        new_task(None).switchtask()
        iotest(args)
        print 'exiting'
        raise SystemExit(0)
    
    if __name__ == '__main__':
        import logging; logging.basicConfig(); logging.getLogger().setLevel('DEBUG')
        main(sys.argv)
