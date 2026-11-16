"""Carry the calling test's explicit request context into parallel service calls."""
from contextvars import copy_context


def map_in_context(pool, function, values):
    context=copy_context()
    return pool.map(lambda value:context.copy().run(function,value),values)
