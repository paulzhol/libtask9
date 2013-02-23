from collections import deque
import random
import threading
from .task import Task, curproc, curtask

_chanlock = threading.Lock()

class AltOp(object):
    CHANNOOP = 0
    CHANSEND = 1
    CHANRECV = 2

    @staticmethod
    def other_op(op):
        return (AltOp.CHANSEND+AltOp.CHANRECV) - op

    def __init__(self, chan, op, value):
        self._chan = chan
        self._op = op
        self._value = value
        self._task = None

    def __repr__(self):
        if self._op == AltOp.CHANSEND:
            return 'chan {!r} send ({})'.format(self._chan, self._value)
        if self._op == AltOp.CHANRECV:
            return 'chan {!r} recv()'.format(self._chan)
        return 'chan {!r} noop ()'.format(self._chan)

    def canexecute(self):
        if self._op == AltOp.CHANNOOP:
            return False
        c = self._chan
        if c._maxlen == 0:
            q = self._chan._getq(AltOp.other_op(self._op))
            return len(q) > 0
        else:
            if self._op == AltOp.CHANSEND:
                return len(c._buf) < c._maxlen
            if self._op == AltOp.CHANRECV:
                return len(c._buf) > 0

    def execute(self):
        assert(self._op in (AltOp.CHANSEND, AltOp.CHANRECV))
        q = self._chan._getq(AltOp.other_op(self._op))

        if len(q) > 0:
            # Rendezvous ops

            other = random.choice(q)

            AltOp._move(self, other)
            other._task._triggered_alt = other

            #altdequeall()
            for altop in other._task._pending_alts:
                altop._chan._dequeue_op(altop)
            other._task._pending_alts = None

            other._task.readytask()
        else:
            # Buffered Channel

            AltOp._move(self, None)

    @staticmethod
    def _move(s, r):
        assert(not ((s is None) and (r is None)))
        assert(s is not None)
        if s._op == AltOp.CHANRECV:
            s, r = r, s
        assert( (s is None) or (s._op == AltOp.CHANSEND) )
        assert( (r is None) or (r._op == AltOp.CHANRECV) )
        
        if s is not None and r is not None and len(s._chan._buf) == 0:
            #print 'move from {} to {}'.format(s, r)
            r._value = s._value
            return
        
        if s is not None:
            s._chan._buf.append(s._value)

        if r is not None:
            assert(len(r._chan._buf) > 0)
            r._value = r._chan._buf.popleft()

def alt(*alts, **kwargs):
    canblock = kwargs.pop('canblock', True)

    global _chanlock
    with _chanlock:
        for a in alts:
            a._task = curtask()
        curtask()._pending_alts = alts
    
        readyops = filter(lambda a: a.canexecute(), alts)
        #print 'alt() readyops: {}'.format(readyops)
        if len(readyops) > 0:
            ready = random.choice(readyops)
            ready.execute()
            return alts.index(ready), ready._value
    
        if not canblock:
            return -1, None
    
        for a in alts:
            a._chan._queue_op(a)

    #_chanlock is not held
    curtask()._state = Task.BLOCKED
    curtask().switchtask()
    
    ready = curproc()._task._triggered_alt
    return alts.index(ready), ready._value

def AltSend(ch, value):
    return AltOp(ch, AltOp.CHANSEND, value)

def AltRecv(ch):
    return AltOp(ch, AltOp.CHANRECV, None)

class Channel(object):
    def __init__(self, nelem):
        self._buf = deque()
        self._maxlen = nelem
        
        self._arecv = []
        self._asend = []

    def recv(self):
        idx, result = alt(AltRecv(self), canblock=True)
        assert(idx == 0)
        return result

    def send(self, value):
        idx, _ = alt(AltSend(self, value), canblock=True)
        assert(idx == 0)

    def nbrecv(self):
        return alt(AltRecv(self), canblock=False)

    def nbsend(self, value):
        return alt(AltSend(self, value), canblock=False)

    def _getq(self, op):
        q = self._arecv
        if op == AltOp.CHANSEND:
            q = self._asend
        return q

    def _queue_op(self, altop):
        if altop._op == AltOp.CHANNOOP:
            return
        q = self._getq(altop._op)
        q.append(altop)

    def _dequeue_op(self, altop):
        q = self._getq(altop._op)
        q.remove(altop)
