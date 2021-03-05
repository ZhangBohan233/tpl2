import compilers.ast as ast


class AstOptimizer:
    def __init__(self, fake_root: ast.BlockStmt, opt_level):
        self.root = fake_root

        self.pre_calculate_lit = opt_level >= 1

    def optimize(self):
        return self.optimize_node(self.root)

    def optimize_node(self, node: ast.Node):
        attrs = dir(node)

        for attr_name in attrs:
            attr = getattr(node, attr_name)
            if isinstance(attr, ast.Node):
                setattr(node, attr_name, self.optimize_node(attr))
            elif isinstance(attr, list):
                for i in range(len(attr)):
                    attr[i] = self.optimize_node(attr[i])

        if self.pre_calculate_lit:
            if isinstance(node, ast.BinaryOperator):
                if isinstance(node.left, ast.FakeIntLit):
                    if isinstance(node.right, ast.FakeIntLit):
                        op_fn = BINARY_OP_INT_RES[node.op]
                        return ast.FakeIntLit(op_fn(node.left.value, node.right.value), node.lfp)
                    elif isinstance(node.right, ast.FakeFloatLit):
                        op_fn = BINARY_OP_FLOAT_RES[node.op]
                        return ast.FakeFloatLit(op_fn(node.left.value, node.right.value), node.lfp)
                elif isinstance(node.left, ast.FakeFloatLit):
                    if isinstance(node.right, ast.FakeIntLit) or isinstance(node.right, ast.FakeFloatLit):
                        op_fn = BINARY_OP_FLOAT_RES[node.op]
                        return ast.FakeFloatLit(op_fn(node.left.value, node.right.value), node.lfp)
            elif isinstance(node, ast.UnaryOperator):
                if isinstance(node.value, ast.FakeIntLit):
                    if node.op == "neg":
                        return ast.FakeIntLit(-node.value.value, node.lfp)
                    elif node.op == "not":
                        return ast.FakeIntLit(int(not node.value.value), node.lfp)
                elif isinstance(node.value, ast.FakeFloatLit):
                    if node.op == "neg":
                        return ast.FakeFloatLit(-node.value.value, node.lfp)

        return node


BINARY_OP_INT_RES = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a // b,
    "%": lambda a, b: a % b,
    "&": lambda a, b: a & b,
    "|": lambda a, b: a | b,
    "^": lambda a, b: a ^ b,
}

BINARY_OP_FLOAT_RES = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
    "%": lambda a, b: a % b,
    "&": lambda a, b: a & b,
    "|": lambda a, b: a | b,
    "^": lambda a, b: a ^ b,
}
