import compilers.tokens_lib as tl
import compilers.ast as ast

PRECEDENCES = {
    "*": 100, "/": 100, "%": 100, "+": 50, "-": 50,
    "*=": 3, "/=": 3, "%=": 3, "+=": 3, "-=": 3,
    ">>": 40, ">>>": 40, "<<": 40, "&": 17, "^": 16, "|": 15,
    ">>=": 3, ">>>=": 3, "<<=": 3, "&=": 3, "|=": 3, "^=": 3,
    ">": 25, "<": 25, ">=": 25, "<=": 25, "==": 20, "!=": 20,
    "and": 6, "or": 5,
    ".": 500, "$": 500, "->": 4, ":": 3, "=": 1, ":=": 1,
    "neg": 200, "not": 200,
    "++": 300, "--": 300, "star": 200, "addr": 200, "as": 150,
    "return": 0
}


class AstBuilder:
    def __init__(self, base_lf):
        self.stack = []
        self.base_lf = base_lf
        self.block = ast.BlockStmt(base_lf)
        self.active = ast.Line(base_lf)

    def add_node(self, node: ast.Node):
        self.stack.append(node)

    def remove_last(self):
        return self.stack.pop()

    def finish_part(self):
        if len(self.stack) > 0:
            has_expr = False
            for node in self.stack:
                if isinstance(node, ast.Buildable) and not node.fulfilled():
                    has_expr = True
            if has_expr:
                self.build_expr()
            self.active.parts.extend(self.stack)
            self.stack.clear()

    def finish_line(self):
        if len(self.stack) > 0:
            self.finish_part()
        self.block.lines.append(self.active)
        self.active = ast.Line(self.base_lf)

    def get_block(self):
        return self.block

    def get_line(self):
        return self.active

    def build_expr(self):
        while True:
            max_pre = -1
            index = 0
            for i in range(len(self.stack)):
                node = self.stack[i]
                if isinstance(node, ast.Buildable) and not node.fulfilled():
                    pre = PRECEDENCES[node.op]
                    if isinstance(node, ast.UnaryBuildable):
                        # eval right side unary operator first
                        # for example, "- -3" is -(-3)
                        if pre >= max_pre:
                            max_pre = pre
                            index = i
                    else:
                        # eval left side binary operator first
                        # for example, "2 * 8 / 4" is (2 * 8) / 4
                        if pre > max_pre:
                            max_pre = pre
                            index = i

            if max_pre == -1:
                break

            expr = self.stack[index]
            if isinstance(expr, ast.UnaryBuildable):
                if expr.operator_at_left:
                    if expr.nullable() and len(self.stack) <= index + 1:
                        value = ast.Nothing(expr.lf)
                    else:
                        value = self.stack.pop(index + 1)
                else:
                    value = self.stack.pop(index - 1)
                expr.value = value
            elif isinstance(expr, ast.BinaryBuildable):
                expr.right = self.stack.pop(index + 1)
                expr.left = self.stack.pop(index - 1)
