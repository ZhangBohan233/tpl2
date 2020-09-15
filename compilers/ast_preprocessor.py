import compilers.ast as ast
import compilers.util as util


class AstPreprocessor:
    def __init__(self, root: ast.BlockStmt):
        self.root = root

        self.literal_bytes = util.initial_literal()

        self.int_literals = util.initial_int_literal_dict()  # int_lit : position in literal_bytes
        self.float_literals = {}
        self.char_literals = {}
        self.str_literals = {}

    def preprocess(self):
        return self.process_node(self.root), self.literal_bytes

    def process_node(self, node: ast.Node) -> ast.Node:
        if isinstance(node, ast.FakeIntLit):
            if node.value in self.int_literals:
                pos = self.int_literals[node.value]
            else:
                pos = len(self.literal_bytes)
                self.literal_bytes.extend(util.int_to_bytes(node.value))
                self.int_literals[node.value] = pos
            return ast.IntLiteral(pos, node.lf)
        elif isinstance(node, ast.FakeFloatLit):
            if node.value in self.float_literals:
                pos = self.float_literals[node.value]
            else:
                pos = len(self.literal_bytes)
                self.literal_bytes.extend(util.float_to_bytes(node.value))
                self.float_literals[node.value] = pos
            return ast.FloatLiteral(pos, node.lf)
        elif isinstance(node, ast.FakeCharLit):
            if node.value in self.char_literals:
                pos = self.char_literals[node.value]
            else:
                pos = len(self.literal_bytes)
                self.literal_bytes.extend(util.char_to_bytes(node.value))
                self.char_literals[node.value] = pos
            return ast.CharLiteral(pos, node.lf)
        elif isinstance(node, ast.FakeStrLit):
            if node.value in self.str_literals:
                pos = self.str_literals[node.value]
            else:
                pos = len(self.literal_bytes)
                self.literal_bytes.extend(util.string_to_bytes(node.value))
                self.str_literals[node.value] = pos
            return ast.StringLiteral(pos, node.lf)
        else:
            attrs = dir(node)

            for attr_name in attrs:
                attr = getattr(node, attr_name)
                if isinstance(attr, ast.Node):
                    setattr(node, attr_name, self.process_node(attr))
                elif isinstance(attr, list):
                    for i in range(len(attr)):
                        attr[i] = self.process_node(attr[i])

            return node
