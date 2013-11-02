static PyMethodDef libtask9_timer_methods[] = {
	{"start_ticker", libtask9_start_ticker, METH_VARARGS},
	{"wait_tick", libtask9_wait_tick, METH_VARARGS},
	{NULL, NULL, 0, NULL}	/* Sentinel */
};

PyMODINIT_FUNC
init_libtask9_timers(void)
{
	Py_InitModule("_libtask9_timers", libtask9_timer_methods);
}
