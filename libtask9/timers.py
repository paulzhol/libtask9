import sys
import logging
from collections import namedtuple
from threading import Lock
from .task import new_proc, new_task
from .channel import Channel, alt, alt_recv
import _libtask9_timers

Millisecond = 1
Second      = 1000 * Millisecond
Minute      = 60 * Second
Hour        = 60 * Minute

_Event = namedtuple('_Event', ('expire_at', 'chan'))

class _Timers(object):
    TIMER_WHEEL_LEN = 257
    TIMER_PERIOD = 100 # miliseconds

    def __init__(self):
        self.ticker = None
        self.now = 0
        self.idx = 0
        self.timer_wheel = tuple(list() for i in xrange(_Timers.TIMER_WHEEL_LEN))
        self.lock = Lock()

    def start(self):
        self.ticker = _libtask9_timers.start_ticker(_Timers.TIMER_PERIOD)
        new_proc(self.ticker_proc, procname='ticker_proc', main_proc=False)

    def register_timer(self, timeout):
        chan = Channel(1)
        with self.lock:
            h = timeout / _Timers.TIMER_PERIOD
            h = (self.idx+h) % _Timers.TIMER_WHEEL_LEN
            self.timer_wheel[h].append(_Event(self.now+timeout, chan))
        return chan

    def process_events(self):
        event_list = self.timer_wheel[self.idx]
        for evt in event_list[:]:
            if self.now >= evt.expire_at:
                evt.chan.nbsend(None)
                event_list.remove(evt)


    def ticker_proc(self):
        while True:
            ticks = _libtask9_timers.wait_tick(self.ticker)
            for i in xrange(ticks):
                with self.lock:
                    self.now += _Timers.TIMER_PERIOD
                    self.idx = (self.idx+1) % _Timers.TIMER_WHEEL_LEN
                    self.process_events()

_timers = None

def init_timers():
    global _timers
    if _timers is not None:
        raise RuntimeError('libtask9 timers are already initialized')
    _timers = _Timers()
    _timers.start()

def after(timeout):
    global _timers
    if _timers is None:
        raise RuntimeError('libtask9 timers were not initialized')
    return _timers.register_timer(timeout)

def sleep(timeout):
    after(timeout).recv()
