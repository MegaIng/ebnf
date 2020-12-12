from __future__ import annotations

import ebnf.dialects
from ebnf.dialect import get_dialect
from ebnf.ebnf import EBNFTree


def parse(dialect: str, text: str) -> EBNFTree:
    d = get_dialect(dialect)
    return d.parse(text)


def unparse(tree: EBNFTree, dialect: str = None) -> str:
    if dialect is None:
        dialect = tree.dialect_name
    d = get_dialect(dialect)
    return d.unparse(tree)

