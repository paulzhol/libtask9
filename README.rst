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

Examples
--------
example1::

    import sys
    from libtask9 import *
    
    def emitter(chan, i):
        while True:
            print 'emitter{}: calling send'.format(i)
            chan.send(i)
    
    def receiver(chan, j):
        while True:
            print 'receiver{}: recv: {}'.format(j, chan.recv())
    
    def taskmain(args):
        print 'taskmain is running'
        chan = Channel(0)
    
        for i in range(10):
            new_proc('emitter-{}'.format(i), emitter, chan, i)
    
        for j in range(5):
            new_proc('receiver-{}'.format(j), receiver, chan, j)
    
        raw_input()
    
    def main(args):
        new_task(taskmain, args).switchtask()
    
    if __name__ == '__main__':
        main(sys.argv)

example2::

    import sys
    import socket
    import time
    from libtask9 import *
    
    def ticker():
        while True:
            time.sleep(2)
            print 'tick'
            curtask().yieldtask()
    
    class Acceptor(object):
        def __init__(self):
            self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            self._s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._s.bind(('0.0.0.0', 8080))
            self._s.listen(1)
        def __call__(self):
            return self._s.accept()
    
    def iotest(args):
        io = IOProc('io1')
        io.start()
        new_task(ticker)
        print 'waiting for io'
        client, addr = io.iocall(Acceptor())
        print 'got: {}'.format(addr)
        client.send('hello!\n')
        client.close()
        io.stop()
    
    def main(args):
        new_task(iotest, args).switchtask()
    
    if __name__ == '__main__':
        main(sys.argv)