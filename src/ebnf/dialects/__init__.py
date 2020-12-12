from __future__ import annotations
from pkgutil import walk_packages


# make sure that all dialects defined here can register themself
for info in walk_packages(__path__, __name__ + '.'):
    __import__(info.name)