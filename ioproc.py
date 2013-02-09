from .channel import Channel
from .task import new_proc

class IOProc(object):
    def __init__(self, name):
        self._name = 'ioproc-{}'.format(name)
        self._c = Channel(0)
        self._creply = Channel(0)
        self._inuse = False

    def start(self):
        new_proc(self._name, self._ioproc_loop, main_proc=False)

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
        return ret

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

            ret = io()
            self._creply.send(ret)
            self._creply.recv()
