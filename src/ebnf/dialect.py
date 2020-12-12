from __future__ import annotations

from abc import ABC, abstractmethod

from ebnf.ebnf import EBNFTree


class EBNFDialect(ABC):
    name: str

    @abstractmethod
    def parse(self, s: str) -> EBNFTree:
        raise NotImplementedError

    @abstractmethod
    def unparse(self, e: EBNFTree) -> str:
        raise NotImplementedError


_dialects: dict[str, EBNFDialect] = {}


def register_dialect(dialect: EBNFDialect, name: str = None):
    if name is None:
        name = dialect.name
    if name in _dialects and _dialects[name] != dialect:
        raise ValueError(f"A different dialect for {name} is already registered.")
    _dialects[name] = dialect


def get_dialect(name: str):
    return _dialects[name]
