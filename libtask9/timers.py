import sys
import math
import errno
import select
import logging
from .task import new_proc, new_task
from .channel import Channel, alt, alt_recv

class _Event(object):
    def __init__(self, timeout, reply_chan):
        self.timeout = timeout
        self.reply_chan = reply_chan

    def __repr__(self):
        return '_Event<timeout: {}>'.format(self.timeout)

class _Timers(object):
    def __init__(self):
        self.events = []
        self.events_guard = _Event(sys.maxint, Channel(0))
        self.events.append(self.events_guard)
        self.tick = Channel(16)
        self.requests = Channel(0)

    def start(self):
        new_proc(self.ticker_proc, procname='ticker_proc', main_proc=False)
        new_task(self.timers_maintask)

    def register_timer(self, timeout):
        timeout = math.ceil(timeout)
        ch = Channel(1)
        self.requests.send(_Event(timeout, ch))
        return ch

    def ticker_proc(self):
        while True:
            try:
                select.select([], [], [], 1.0)
                self.tick.send(True)
            except select.error as e:
                if e.errno == errno.EINTR:
                    continue
                raise

    def timers_maintask(self):
        while True:
            idx, result = alt(
                alt_recv(self.tick),
                alt_recv(self.requests),
                canblock = True
            )

            if idx == 0:
                logging.debug('tick, events: {}'.format(self.events))
                while self.events[0] != self.events_guard:
                    self.events[0].timeout -= 1
                    if self.events[0].timeout <= 0:
                        event = self.events.pop(0)
                        event.reply_chan.send(True)
                    else:
                        break

            elif idx == 1:
                self._add_event(result)

    def _add_event(self, new_evt):
        logging.debug('request for {}'.format(new_evt.timeout))
        for idx, evt in enumerate(self.events):
            if new_evt.timeout <= evt.timeout:
                break
            new_evt.timeout -= evt.timeout

        self.events.insert(idx, new_evt)
        if evt != self.events_guard:
            evt.timeout -= new_evt.timeout

        logging.debug('events: {}'.format(self.events))

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
