from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from functools import partial
from typing import Any

from lark import Tree


class EBNFTree(Tree):
    dialect_name: str

    def __init__(self, dialect_name, data, children, meta=None):
        super(EBNFTree, self).__init__(data, children, meta)
        self.dialect_name = dialect_name
        
    def __repr__(self):
        return f"{type(self).__name__}({self.dialect_name!r}, {self.data!r}, {self.children!r})"


def ebnf_tree_fact(dialect_name: str):
    return partial(EBNFTree, dialect_name)
