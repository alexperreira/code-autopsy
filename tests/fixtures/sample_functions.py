# Fixture file for PythonAnalyzer tests.
# Line numbers are intentional — do not reorder without updating tests.

import os
import sys
from pathlib import Path


def simple(x, y):          # line 9 — 2 args, depth 0, 3 lines
    z = x + y
    return z               # end line 11


def with_branch(value):    # line 14 — 1 arg, depth 1, 5 lines
    if value > 0:
        return value
    else:
        return -value      # end line 18


def nested_loops(items):   # line 21 — 1 arg, depth 2, 6 lines
    for item in items:
        for sub in item:
            print(sub)
        print(item)
    return items           # end line 26


class MyClass:             # line 29 — 2 methods
    def __init__(self, a, b):   # line 30 — 2 args (self excluded), depth 0, 3 lines
        self.a = a
        self.b = b              # end line 32

    def compute(self, x):       # line 34 — 1 arg (self excluded), depth 1, 4 lines
        if x > self.a:
            return x * self.b
        return 0                # end line 37


async def async_fn(*, key):    # line 40 — 1 kwonly arg, depth 0, 2 lines
    return key                 # end line 41
