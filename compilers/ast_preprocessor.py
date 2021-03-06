import compilers.ast as ast
import compilers.util as util


class AstPreprocessor:
    def __init__(self, root: ast.BlockStmt):
        self.root = root

        self.literal_bytes = util.initial_literal()

        self.int_literals = util.initial_int_literal_dict()  # int_lit : position in literal_bytes
        self.float_literals = {}
        self.char_literals = {}
        self.byte_literals = {}
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
            return ast.IntLiteral(pos, node.lfp)
        elif isinstance(node, ast.FakeFloatLit):
            if node.value in self.float_literals:
                pos = self.float_literals[node.value]
            else:
                pos = len(self.literal_bytes)
                self.literal_bytes.extend(util.float_to_bytes(node.value))
                self.float_literals[node.value] = pos
            return ast.FloatLiteral(pos, node.lfp)
        elif isinstance(node, ast.FakeCharLit):
            if node.value in self.char_literals:
                pos = self.char_literals[node.value]
            else:
                pos = len(self.literal_bytes)
                self.literal_bytes.extend(util.char_to_bytes(node.value))
                self.char_literals[node.value] = pos
            return ast.CharLiteral(pos, node.lfp)
        elif isinstance(node, ast.FakeByteLit):
            if node.value in self.byte_literals:
                pos = self.byte_literals[node.value]
            else:
                pos = len(self.literal_bytes)
                self.literal_bytes.append(node.value & 0xff)
                self.byte_literals[node.value] = pos
            return ast.ByteLiteral(pos, node.lfp)
        elif isinstance(node, ast.FakeStrLit):
            if node.value in self.str_literals:
                pos = self.str_literals[node.value]
            else:
                pos = len(self.literal_bytes)
                self.literal_bytes.extend(util.string_to_bytes(node.value))
                self.str_literals[node.value] = pos
            sl = ast.CharArrayLiteral(pos, node.lfp)
            creation = ast.NewExpr(node.lfp)
            creation.value = ast.FunctionCall(ast.NameNode("String", node.lfp),
                                              ast.Line(node.lfp, sl),
                                              node.lfp)
            return creation
        elif isinstance(node, ast.BinaryOperatorAssignment):
            left = self.process_node(node.left)
            right = self.process_node(node.right)
            bo = ast.BinaryOperator(node.op[:-1], node.op_type, node.lfp)
            bo.left = left
            bo.right = right
            ass = ast.Assignment(node.lfp)
            ass.left = left
            ass.right = bo
            return ass
        elif isinstance(node, ast.DotExpr):
            left = self.process_node(node.left)
            right = self.process_node(node.right)
            if isinstance(right, ast.IndexingExpr):
                new_dot = ast.DotExpr(node.lfp)
                new_dot.left = left
                new_dot.right = right.indexing_obj
                return ast.IndexingExpr(new_dot, right.args, node.lfp)
            # elif isinstance(right, ast.FunctionCall):
            #     new_dot = ast.DotExpr(node.lf)
            #     new_dot.left = left
            #     new_dot.right = right.call_obj
            #     return ast.FunctionCall(new_dot, right.args, node.lf)

            node.left = left
            node.right = right
            return node

        attrs = dir(node)

        for attr_name in attrs:
            attr = getattr(node, attr_name)
            if isinstance(attr, ast.Node):
                setattr(node, attr_name, self.process_node(attr))
            elif isinstance(attr, list):
                for i in range(len(attr)):
                    attr[i] = self.process_node(attr[i])

        return node
