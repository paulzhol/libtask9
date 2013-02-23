import sys
import traceback
from collections import deque
import greenlet
import threading

class Task(object):
    RUNNING = 0
    READY   = 1
    BLOCKED = 2
    FINISHED = 3

    def __init__(self, proc, run, *run_args, **run_kwargs):
        def _wrap_task():
            try:
                run(*run_args, **run_kwargs)
            except:
                exctype, excval, trace = sys.exc_info()
                traceback.print_tb(trace)
                traceback.print_exc()
                del(trace)
            finally:
                self._state = Task.FINISHED
                self._proc = None
                proc._remove_task(self)

        self._proc = proc
        if run is None:
            self._ctx = greenlet.getcurrent()
        else:
            self._ctx = greenlet.greenlet(_wrap_task, proc._sched_ctx)
        self._state = Task.READY
        self._pending_alts = None
        self._triggered_alt = None

    def yieldtask(self):
        self.readytask()
        self.switchtask()

    def switchtask(self):
        self._proc._sched_ctx.switch()

    def readytask(self):
        self._state = Task.READY
        self._proc._ready_task(self)

class Proc(object):
    def __init__(self, name=None):
        self._name = name

        self._lock = threading.RLock()
        self._task = None
        self._tasks = []
        self._runq = deque()
        self._runq_empty = threading.Condition(self._lock)
        self._sched_ctx = None
        self._timers = None

    def _init_sched_ctx(self):
        self._sched_ctx = greenlet.greenlet(self._schedule)

    def _add_task(self, t):
        assert(isinstance(t, Task))
        with self._lock:
            self._tasks.append(t)
            self._runq.append(t)

    def _ready_task(self, t):
        assert(isinstance(t, Task))
        assert(t in self._tasks)
        with self._lock:
            self._runq.append(t)
            if len(self._runq) == 1:
                self._runq_empty.notify()

    def _remove_task(self, t):
        assert(t._state != Task.RUNNING)

        with self._lock:
            assert(t not in self._runq)
            self._tasks.remove(t)

    def _schedule(self):
        while True:
            with self._lock:
                if len(self._tasks) == 0:
                    print 'proc {} done'.format(self._name)
                    return
                
                while len(self._runq) == 0:
                    self._runq_empty.wait()
                self._task = self._runq.popleft()

            self._task._state = Task.RUNNING
            print 'proc {} switching to {}'.format(self._name, self._task)
            self._task._ctx.switch()

_tls = threading.local()
def curproc():
    global _tls
    try:
        return _tls.curproc
    except AttributeError:
        p = Proc('mainproc')
        _setcurproc(p)
        p._init_sched_ctx()
        return p

def _setcurproc(p):
    global _tls
    _tls.curproc = p

def curtask():
    return curproc()._task

def new_proc(run, *run_args, **run_kwargs):
    procname = run_kwargs.pop('procname', '')
    main_proc = run_kwargs.pop('main_proc', False)
    p = Proc(procname)

    def _procmain():
        _setcurproc(p)
        # greenlet req: scheduler context must be created when running on the target thread
        p._init_sched_ctx()
        t = new_task(run, *run_args, **run_kwargs)
        t.switchtask()

    p_thread = threading.Thread(target=_procmain, name=procname)
    p_thread.daemon = not main_proc
    p_thread.start()
    return p

def new_task(run, *run_args, **run_kwargs):
    t = Task(curproc(), run, *run_args, **run_kwargs)
    curproc()._add_task(t)
    return t
