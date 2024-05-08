# -*- coding: utf-8 -*-
# utils/collections.py

try:
    from collections import Sequence, Mapping, Set, Callable
except ImportError:
    # since Python 3.10
    from collections.abc import Sequence, Mapping, Set, Callable

