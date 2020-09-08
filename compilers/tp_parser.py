import compilers.tokens_lib as tl
import compilers.ast as ast
import compilers.ast_builder as ab
import compilers.util as util
import compilers.errors as errs


class Parser:
    def __init__(self, tokens: tl.CollectiveElement):
        self.tokens = tokens
        self.literal_bytes = bytearray()
        self.var_level = ast.VAR_VAR

        self.int_literals = {}  # int_lit : position in literal_bytes
        self.float_literals = {}
        self.char_literals = {}

        self.symbol_lib = {
            "=": self.process_assign,
            ":": self.process_declare,
            ",": self.process_comma,
            ";": self.process_eol,
            "fn": self.process_fn,
            "var": self.process_var,
            "const": self.process_const,
            "return": self.process_return,
            "->": self.process_right_arrow,
            "if": self.process_if_stmt,
            "while": self.process_while_stmt,
            "for": self.process_for_stmt,
            "require": self.process_require,
            "break": self.process_break,
            "continue": self.process_continue
        }

    def parse(self):
        return self.parse_as_block(self.tokens), self.literal_bytes

    # processor methods of single identifiers
    #
    # returns None or 0 if this processor does not push the index,
    # otherwise, return the last index used for this processor
    # Note: do not return the index of the next

    def process_assign(self, p, i, builder, lf):
        builder.add_node(ast.Assignment(lf))

    def process_declare(self, parent: tl.CollectiveElement, index: int, builder: ab.AstBuilder, lf: tl.LineFile):
        builder.add_node(ast.Declaration(self.var_level, lf))

    def process_fn(self, parent: tl.CollectiveElement, index: int, builder: ab.AstBuilder, lf: tl.LineFile):
        index += 1
        next_ele = parent[index]
        if isinstance(next_ele, tl.AtomicElement):
            fn_name = next_ele.atom.identifier
            index += 1
        else:
            fn_name = None
        param_list = parent[index]
        params = self.parse_as_line(param_list)
        prob_arrow = parent[index + 1]
        if identifier_of(prob_arrow, "->"):
            builder.add_node(ast.FunctionTypeExpr(params, lf))
            return index

        rtype_list = tl.CollectiveElement(tl.CE_BRACKET, None, lf)
        while not (tl.is_brace(parent[index]) or identifier_of(parent[index], ";")):
            rtype_list.append(parent[index])
            index += 1
        rtype = self.parse_as_part(rtype_list)
        body_list = parent[index]
        if identifier_of(body_list, ";"):
            body = None
        else:
            body = self.parse_as_block(body_list)

        builder.add_node(ast.FunctionDef(fn_name, params, rtype, body, lf))
        return index

    def process_eol(self, p, i, builder, lf):
        builder.finish_part()
        builder.finish_line()
        self.var_level = ast.VAR_VAR

    def process_comma(self, p, i, builder, lf):
        builder.finish_part()

    def process_var(self, p, i, b, lf):
        self.var_level = ast.VAR_VAR

    def process_const(self, p, i, b, lf):
        self.var_level = ast.VAR_CONST

    def process_return(self, p, i, builder, lf):
        builder.add_node(ast.ReturnStmt(lf))

    def process_right_arrow(self, parent: tl.CollectiveElement, index: int, builder: ab.AstBuilder, lf: tl.LineFile):
        builder.add_node(ast.RightArrowExpr(lf))

    def process_if_stmt(self, parent: tl.CollectiveElement, index, builder, lf):
        index += 1
        condition_list = tl.CollectiveElement(tl.CE_BRACKET, lf, None)
        item = parent[index]
        while not (isinstance(item, tl.CollectiveElement) and item.is_brace()):
            condition_list.append(item)
            index += 1
            item = parent[index]
        cond = self.parse_as_part(condition_list)
        body = self.parse_as_block(item)
        if index + 1 < len(parent) and identifier_of(parent[index + 1], "else"):
            index += 2
            else_block = self.parse_as_block(parent[index])
        else:
            else_block = None
        ifs = ast.IfStmt(cond, body, else_block, lf)
        builder.add_node(ifs)
        return index

    def process_while_stmt(self, parent: tl.CollectiveElement, index: int, builder: ab.AstBuilder, lf: tl.LineFile):
        index += 1
        item = parent[index]
        cond_list = tl.CollectiveElement(tl.CE_BRACKET, lf, None)
        while not (isinstance(item, tl.CollectiveElement) and item.is_brace()):
            cond_list.append(item)
            index += 1
            item = parent[index]

        cond = self.parse_as_part(cond_list)
        body = self.parse_as_block(item)
        builder.add_node(ast.WhileStmt(cond, body, lf))

    def process_for_stmt(self, parent: tl.CollectiveElement, index: int, builder: ab.AstBuilder, lf: tl.LineFile):
        index += 1
        item = parent[index]
        cond_list = tl.CollectiveElement(tl.CE_BRACKET, lf, None)
        while not (isinstance(item, tl.CollectiveElement) and item.is_brace()):
            cond_list.append(item)
            index += 1
            item = parent[index]

        cond = self.parse_as_block(cond_list)
        body = self.parse_as_block(item)
        builder.add_node(ast.ForStmt(cond, body, lf))

    def process_break(self, p, i, builder, lf):
        builder.add_node(ast.BreakStmt(lf))

    def process_continue(self, p, i, builder, lf):
        builder.add_node(ast.ContinueStmt(lf))

    def process_require(self, parent: tl.CollectiveElement, index: int, builder: ab.AstBuilder, lf: tl.LineFile):
        index += 1
        item = parent[index]
        if isinstance(item, tl.CollectiveElement):
            content = self.parse_as_block(item)
        else:
            bracket = tl.CollectiveElement(tl.CE_BRACKET, lf, None)
            bracket.append(item)
            index += 1
            while not identifier_of(parent[index], ";"):
                bracket.append(parent[index])
                index += 1
            content = self.parse_as_part(bracket)
        builder.add_node(ast.RequireStmt(content, lf))
        self.process_eol(parent, index, builder, lf)
        return index

    # parser of collective elements

    def parse_as_block(self, lst: tl.CollectiveElement):
        builder = self.parse_as_builder(lst)
        self.var_level = ast.VAR_VAR
        builder.finish_part()
        builder.finish_line()
        return builder.get_block()

    def parse_as_line(self, lst: tl.CollectiveElement):
        builder = self.parse_as_builder(lst)
        self.var_level = ast.VAR_VAR
        builder.finish_part()
        return builder.get_line()

    def parse_as_part(self, lst: tl.CollectiveElement):
        builder = self.parse_as_builder(lst)
        builder.finish_part()
        line = builder.get_line()
        if len(line.parts) != 1:
            raise errs.TplParseError("Line should only contain 1 part. ", lst.lf)
        return line.parts[0]

    def parse_as_builder(self, lst: tl.CollectiveElement) -> ab.AstBuilder:
        builder = ab.AstBuilder(lst.lf)
        i = 0
        while i < len(lst):
            i = self.parse_one(lst, i, builder)
        return builder

    def parse_one(self, parent: tl.CollectiveElement, index: int, builder: ab.AstBuilder) -> int:
        ele: tl.Element = parent[index]
        if isinstance(ele, tl.AtomicElement):
            token = ele.atom
            lf = token.lf
            if isinstance(token, tl.IntToken):
                if token.value in self.int_literals:
                    pos = self.int_literals[token.value]
                else:
                    pos = len(self.literal_bytes)
                    self.literal_bytes.extend(util.int_to_bytes(token.value))
                builder.add_node(ast.IntLiteral(pos, lf))
            elif isinstance(token, tl.FloatToken):
                pass
            elif isinstance(token, tl.CharToken):
                pass
            elif isinstance(token, tl.StrToken):
                pass
            elif isinstance(token, tl.IdToken):
                symbol = token.identifier
                if symbol == "-":
                    if index < 1 or is_unary(parent[index - 1]):
                        builder.add_node(ast.UnaryOperator("neg", ast.UNA_ARITH, lf))
                    else:
                        builder.add_node(ast.BinaryOperator("-", ast.BIN_ARITH, lf))
                elif symbol == "*":
                    if index < 1 or is_unary(parent[index - 1]):
                        builder.add_node(ast.StarExpr(lf))
                    else:
                        builder.add_node(ast.BinaryOperator("*", ast.BIN_ARITH, lf))
                elif symbol == "&":
                    if index < 1 or is_unary(parent[index - 1]):
                        builder.add_node(ast.AddrExpr(lf))
                    else:
                        builder.add_node(ast.BinaryOperator("&", ast.BIN_BITWISE, lf))
                elif symbol in tl.ARITH_BINARY:
                    builder.add_node(ast.BinaryOperator(symbol, ast.BIN_ARITH, lf))
                elif symbol in tl.LOGICAL_BINARY:
                    builder.add_node(ast.BinaryOperator(symbol, ast.BIN_LOGICAL, lf))
                elif symbol in tl.BITWISE_BINARY:
                    builder.add_node(ast.BinaryOperator(symbol, ast.BIN_BITWISE, lf))
                elif symbol in tl.LAZY_BINARY:
                    builder.add_node(ast.BinaryOperator(symbol, ast.BIN_LAZY, lf))
                elif symbol in tl.ARITH_UNARY:
                    builder.add_node(ast.UnaryOperator(symbol, ast.UNA_ARITH, lf))
                elif symbol in tl.LOGICAL_UNARY:
                    builder.add_node(ast.UnaryOperator(symbol, ast.UNA_LOGICAL, lf))
                elif symbol in tl.ARITH_BINARY_ASS:
                    builder.add_node(ast.BinaryOperatorAssignment(symbol, ast.BIN_ARITH, lf))
                elif symbol in tl.BITWISE_BINARY_ASS:
                    builder.add_node(ast.BinaryOperatorAssignment(symbol, ast.BIN_BITWISE, lf))
                elif symbol in tl.FAKE_TERNARY:
                    builder.add_node(ast.FakeTernaryOperator(symbol, lf))
                elif symbol in self.symbol_lib:
                    ftn = self.symbol_lib[symbol]
                    res = ftn(parent, index, builder, lf)
                    if res:
                        index = res
                else:
                    builder.add_node(ast.NameNode(symbol, lf))

            else:
                raise Exception("Unexpected error. ")
        elif isinstance(ele, tl.CollectiveElement):
            if ele.is_bracket():
                lf = ele.lf
                if index > 0:
                    prob_call_obj = parent[index - 1]
                    if isinstance(prob_call_obj, tl.AtomicElement) and is_call(prob_call_obj.atom):
                        args = self.parse_as_line(ele)
                        call_obj = builder.remove_last()
                        call = ast.FunctionCall(call_obj, args, lf)
                        builder.add_node(call)
                        return index + 1

        else:
            raise Exception("Unexpected error. ")

        return index + 1


UNARY_LEADING = {
    ";", ":", "=", "->", ".", ","
}


def identifier_of(ele: tl.Element, target: str) -> bool:
    return isinstance(ele, tl.AtomicElement) and isinstance(ele.atom, tl.IdToken) and ele.atom.identifier == target


def is_unary(leading_ele: tl.Element) -> bool:
    if isinstance(leading_ele, tl.AtomicElement):
        token = leading_ele.atom
        if isinstance(token, tl.IdToken):
            symbol = token.identifier
            if symbol in UNARY_LEADING:
                return True
            else:
                return symbol in tl.ALL_BINARY or symbol in tl.RESERVED
        else:
            return not (isinstance(token, tl.IntToken) or
                        isinstance(token, tl.FloatToken) or
                        isinstance(token, tl.CharToken))
    else:
        return not (isinstance(leading_ele, tl.CollectiveElement) and leading_ele.is_bracket())


def is_call(token_before: tl.Token) -> bool:
    if isinstance(token_before, tl.IdToken):
        symbol = token_before.identifier
        return symbol.isidentifier() and symbol not in tl.RESERVED
    return False
