from __future__ import annotations

from lark import Lark, Transformer
from lark.reconstruct import Reconstructor

from ebnf.dialect import EBNFDialect, register_dialect
from ebnf.ebnf import EBNFTree, ebnf_tree_fact

lark_parser = Lark.open_from_package('lark', 'grammars/lark.lark', parser='lalr', tree_class=ebnf_tree_fact('lark'),
                                     propagate_positions=True)
lark_reconstructor = Reconstructor(lark_parser, {'_NL': '\n'})


class LarkDialect(EBNFDialect):
    name = 'lark'

    def parse(self, s: str) -> EBNFTree:
        tree = lark_parser.parse(s)
        return tree

    def unparse(self, e: EBNFTree) -> str:
        return lark_reconstructor.reconstruct(e)


register_dialect(LarkDialect())
