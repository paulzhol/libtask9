import sys
from .channel import Channel
from .task import new_proc

class IOProc(object):
    NO_EXC = (None, None, None)

    def __init__(self, name):
        self._name = 'ioproc-{}'.format(name)
        self._c = Channel(0)
        self._creply = Channel(0)
        self._inuse = False

    def start(self):
        new_proc(self._ioproc_loop, procname=self._name, main_proc=False)

    def stop(self):
        if self._inuse:
            raise RuntimeError('ioproc still in use')
        self._c.send(None)

    def iocall(self, io):
        assert(callable(io))

        self._c.send(self)
        assert(not self._inuse)
        self._inuse = True
        self._creply.send(io)

        ret = self._creply.recv()
        self._inuse = False
        self._creply.send(None)
        if ret['exc'] != IOProc.NO_EXC:
            exc_info = ret['exc']
            raise exc_info[0], exc_info[1], exc_info[2]
        return ret['result']

    def _ioproc_loop(self):
        while True:
            # _c and _creply channels are not buffered, first recv acquires the ioproc.
            # Second recv passes the io request.
            x = self._c.recv()
            if x is None:
                return
            assert(x is self)

            io = self._creply.recv()
            if io is None:
                return

            ret = dict(result=None, exc=IOProc.NO_EXC)
            try:
                ret['result'] = io()
            except:
                ret['exc'] = sys.exc_info()
            finally:
                self._creply.send(ret)

            self._creply.recv()
