#include <Python.h>
#include <pthread.h>
#include <sys/time.h>
#include <stdio.h>
#include "ns.h"

static const char TIMER_CAPSULE[] = "_libtask9_timers.timer";

typedef struct PthreadsTimer PthreadsTimer;
struct PthreadsTimer {
	pthread_mutex_t lock;
	pthread_cond_t  cond;
	int             interval_msec;
};

static void
libtask9_ticker_dtor(PyObject *obj)
{
	PthreadsTimer *timer;

	timer = (PthreadsTimer *)PyCapsule_GetPointer(obj, TIMER_CAPSULE);
	pthread_mutex_destroy(&timer->lock);
	pthread_cond_destroy(&timer->cond);
	free(timer);
}

static PyObject *
libtask9_start_ticker(PyObject *self, PyObject *args)
{
	int interval_msec;
	PthreadsTimer *timer;
	int err;

	if(!PyArg_ParseTuple(args, "i", &interval_msec))
		return NULL;

	timer = malloc(sizeof(PthreadsTimer));
	if(!timer)
		return PyErr_NoMemory();

	err = pthread_mutex_init(&timer->lock, NULL);
	if(err != 0) {
		free(timer);
		return PyErr_Format(PyExc_OSError, "pthread_mutex_init failed: %d (%s)", err, strerror(err));
	}
	err = pthread_cond_init(&timer->cond, NULL);
	if(err != 0) {
		pthread_mutex_destroy(&timer->lock);
		free(timer);
		return PyErr_Format(PyExc_OSError, "pthread_cond_init failed: %d (%s)", err, strerror(err));
	}

	pthread_mutex_lock(&timer->lock);
	timer->interval_msec = interval_msec;
	return PyCapsule_New(timer, TIMER_CAPSULE, libtask9_ticker_dtor);
}

static const int debug_wakeups = 0;

static PyObject *
libtask9_wait_tick(PyObject *self, PyObject *args)
{
	PyObject *timer_capsule;
	PthreadsTimer *timer;
	struct timeval now, future;
	struct timespec abstime;
	int err;

	if(!PyArg_ParseTuple(args, "O", &timer_capsule))
		return NULL;
	Py_INCREF(timer_capsule);

	timer = PyCapsule_GetPointer(timer_capsule, TIMER_CAPSULE);

	Py_BEGIN_ALLOW_THREADS
	gettimeofday(&now, NULL);
	abstime.tv_nsec = (now.tv_usec * NS_IN_USEC) + (timer->interval_msec * NS_IN_MSEC);
	abstime.tv_sec = now.tv_sec + (abstime.tv_nsec / NS_IN_SEC);
	abstime.tv_nsec %= NS_IN_SEC;
	future.tv_sec = abstime.tv_sec;
	future.tv_usec = abstime.tv_nsec / NS_IN_USEC;
	for(;;) {
		err = pthread_cond_timedwait(&timer->cond, &timer->lock, &abstime);
		if(err == ETIMEDOUT)
			break;
		if(err == 0) {
			gettimeofday(&now, NULL);
			if((now.tv_sec < future.tv_sec) ||
				((now.tv_sec == future.tv_sec) && (now.tv_usec < future.tv_usec))) {
				/* spurious wakeup */
if(debug_wakeups) fprintf(stderr, "spurious wakeup!\n");
				continue;
			}
		}

		Py_BLOCK_THREADS
		Py_DECREF(timer_capsule);
		return PyErr_Format(PyExc_OSError, "pthread_cond_timedwait failed: %d (%s)",
			err, strerror(err));
	}
	Py_END_ALLOW_THREADS

	Py_DECREF(timer_capsule);
	return PyInt_FromLong(1);
}

#include "common.c"
