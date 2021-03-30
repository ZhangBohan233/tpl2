import compilers.tokens_lib as tl
import compilers.errors as errs
import compilers.ast as ast

PRECEDENCES = {
    "*": 100, "/": 100, "%": 100, "+": 50, "-": 50,
    "*=": 3, "/=": 3, "%=": 3, "+=": 3, "-=": 3,
    ">>": 40, ">>>": 40, "<<": 40, "&": 17, "^": 16, "|": 15,
    ">>=": 3, ">>>=": 3, "<<=": 3, "&=": 3, "|=": 3, "^=": 3,
    ">": 25, "<": 25, ">=": 25, "<=": 25, "==": 20, "!=": 20, "instanceof": 25, "is": 20, "is not": 20,
    "and": 6, "or": 5,
    ".": 500, "$": 500, "->": 4, ":": 3, "=": 1, ":=": 1, "::": 5, "in": 2,  # 'in' lower than ':'
    "neg": 200, "not": 200,
    "++": 300, "--": 300,
    "star": 200, "addr": 200, "as": 150, "new": 550, "del": 1,
    "return": 0, "yield": 0
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
                        value = ast.Nothing(expr.lfp)
                    else:
                        value = self.stack.pop(index + 1)
                else:
                    value = self.stack.pop(index - 1)
                expr.value = value
            elif isinstance(expr, ast.BinaryBuildable):
                expr.right = self.stack.pop(index + 1)
                expr.left = self.stack.pop(index - 1)


def parse_switch(cond: ast.Expression, body: ast.BlockStmt, lf):
    expr_level = 0  # 0 for not initialized, 1 for expr, 2 for stmt
    default_case = None
    cases = []
    if len(body) == 1 or (len(body) == 2 and len(body[1]) == 0):
        for part in body[0]:
            if isinstance(part, ast.CaseExpr):
                if expr_level == 2:
                    raise errs.TplParseError("Cases must all be expressions or statements. ", lf)
                else:
                    expr_level = 1
            elif isinstance(part, ast.CaseStmt):
                if expr_level == 1:
                    raise errs.TplParseError("Cases must all be expressions or statements. ", lf)
                else:
                    expr_level = 2
            else:
                raise errs.TplParseError("Only 'case' or 'default'. ", lf)

            if part.cond is None:  # is default
                if default_case is None:
                    default_case = part
                else:
                    raise errs.TplParseError("Switch/cond can have at most 1 default case. ", lf)
            else:
                cases.append(part)

        if expr_level == 1:
            if default_case is None:
                raise errs.TplParseError("Switch-case expression must cover all possibilities. ", lf)
            return ast.SwitchExpr(cond, cases, default_case, lf)
        elif expr_level == 2:
            return ast.SwitchStmt(cond, cases, default_case, lf)
        else:
            assert len(cases) == 0 and default_case is None
            return ast.SwitchStmt(cond, cases, default_case, lf)

    elif len(body) != 0:
        raise errs.TplParseError("Switch parse error. ", lf)
