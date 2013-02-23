import select
import logging
from .task import new_proc, new_task, curproc
from .channel import Channel, alt, AltRecv

class _Event(object):
    def __init__(self, timeout, reply_chan):
        self.timeout = timeout
        self.reply_chan = reply_chan

    def __repr__(self):
        return '_Event<timeout: {}>'.format(self.timeout)

class _Timers(object):
    def __init__(self):
        self.events = []
        self.tick = Channel(0)
        self.requests = Channel(0)

    def start(self):
        new_proc(self.ticker_proc, procname='ticker_proc', main_proc=False)
        new_task(self.timers_maintask)

    def after(self, timeout):
        ch = Channel(1)
        self.requests.send(_Event(timeout, ch))
        return ch

    def ticker_proc(self):
        while True:
            select.select([], [], [], 1.0)
            self.tick.send(True)

    def timers_maintask(self):
        ticks = 0
        while True:
            idx, result = alt(
                AltRecv(self.tick),
                AltRecv(self.requests),
                canblock = True
            )

            if idx == 0:
                logging.debug('tick')
                if len(self.events) == 0:
                    continue

                ticks += 1
                if self.events[0].timeout == ticks:
                    ticks = 0
                    event = self.events.pop(0)
                    event.reply_chan.send(True)

            elif idx == 1:
                logging.debug('request for {}'.format(result.timeout))
                if len(self.events) == 0:
                    self.events.append(result)
                    logging.debug('ticks:{} events: {}'.format(ticks, self.events))
                    continue

                assert(self.events[0].timeout >= ticks)
                self.events[0].timeout -= ticks
                ticks = 0

                event_inserted = False
                for i in range(len(self.events)):
                    logging.debug('i:{} result:{}'.format(i, result))
                    if result.timeout > self.events[i].timeout:
                        result.timeout -= self.events[i].timeout
                    else:
                        self.events[i].timeout -= result.timeout
                        self.events.insert(i, result)
                        event_inserted = True
                        break
                if not event_inserted:
                    self.events.append(result)

                logging.debug('ticks:{} events: {}'.format(ticks, self.events))

def after(timeout):
    if curproc()._timers is None:
        curproc()._timers = _Timers()
        curproc()._timers.start()
    return curproc()._timers.after(timeout)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    new_task(None).switchtask()
    timeout4 = after(4)
    timeout2 = after(1)
    timeout9 = after(9)
    timeout9.recv()
