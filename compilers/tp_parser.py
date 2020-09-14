import compilers.tokens_lib as tl
import compilers.ast as ast
import compilers.ast_builder as ab
import compilers.util as util
import compilers.errors as errs


def process_empty(p, i, b, lf):
    pass


class Parser:
    def __init__(self, tokens: tl.CollectiveElement):
        self.tokens = tokens
        self.literal_bytes = util.initial_literal()
        self.var_level = ast.VAR_VAR

        self.int_literals = util.initial_int_literal_dict()  # int_lit : position in literal_bytes
        self.float_literals = {}
        self.char_literals = {}
        self.str_literals = {}

        self.special_binary = {
            "=": ast.Assignment,
            ".": ast.Dot,
            "->": ast.RightArrowExpr,
            "as": ast.AsExpr,
            "$": ast.DollarExpr
        }

        self.symbol_lib = {
            ":": self.process_declare,
            ",": self.process_comma,
            ";": self.process_eol,
            "fn": self.process_fn,
            "var": self.process_var,
            "const": self.process_const,
            "return": self.process_return,
            "if": self.process_if_stmt,
            "while": self.process_while_stmt,
            "for": self.process_for_stmt,
            "require": self.process_require,
            "break": self.process_break,
            "continue": self.process_continue,
            "import": self.process_import,
            "export": self.process_export,
            "struct": self.process_struct,
            "\n": process_empty
        }

    def parse(self):
        return self.parse_as_block(self.tokens), self.literal_bytes

    # processor methods of single identifiers
    #
    # returns None or 0 if this processor does not push the index,
    # otherwise, return the last index used for this processor
    # In other words, returns the extra number of elements processed
    #
    # Note: do not return the index of the next

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
        if tl.identifier_of(prob_arrow, "->"):
            builder.add_node(ast.FunctionTypeExpr(params, lf))
            return index

        index += 1
        rtype_list = tl.CollectiveElement(tl.CE_BRACKET, lf, None)
        while not (tl.is_brace(parent[index]) or tl.identifier_of(parent[index], ";")):
            rtype_list.append(parent[index])
            index += 1
        rtype = self.parse_as_part(rtype_list)
        body_list = parent[index]
        if tl.identifier_of(body_list, ";"):
            body = None
        else:
            body = self.parse_as_block(body_list)

        builder.add_node(ast.FunctionDef(fn_name, params, rtype, body, lf))
        return index

    def process_eol(self, p, i, builder: ab.AstBuilder, lf):
        builder.finish_part()
        builder.finish_line()
        self.var_level = ast.VAR_VAR

    def process_comma(self, p, i, builder: ab.AstBuilder, lf):
        builder.finish_part()

    def process_var(self, p, i, b, lf):
        self.var_level = ast.VAR_VAR

    def process_const(self, p, i, b, lf):
        self.var_level = ast.VAR_CONST

    def process_return(self, p, i, builder: ab.AstBuilder, lf):
        builder.add_node(ast.ReturnStmt(lf))

    def process_if_stmt(self, parent: tl.CollectiveElement, index, builder, lf):
        index += 1
        condition_list = tl.CollectiveElement(tl.CE_BRACKET, lf, None)
        item = parent[index]
        while not (isinstance(item, tl.CollectiveElement) and item.is_brace()):
            condition_list.append(item)
            index += 1
            item = parent[index]
            if tl.identifier_of(item, "then"):  # is a if-expr instead of if-stmt
                return self.process_if_expr(condition_list, parent, index, builder, lf)
        cond = self.parse_as_part(condition_list)
        body = self.parse_as_block(item)
        if index + 1 < len(parent) and tl.identifier_of(parent[index + 1], "else"):
            index += 2
            else_block = self.parse_as_block(parent[index])
        else:
            else_block = None
        ifs = ast.IfStmt(cond, body, else_block, lf)
        builder.add_node(ifs)
        return index

    def process_if_expr(self, cond_list: tl.CollectiveElement,
                        parent: tl.CollectiveElement, index: int, builder: ab.AstBuilder, lf: tl.LineFile):
        cond = self.parse_as_part(cond_list)
        index += 1
        then_list = tl.CollectiveElement(tl.CE_BRACKET, lf, None)
        while not tl.identifier_of(parent[index], "else"):
            then_list.append(parent[index])
            index += 1
        then_expr = self.parse_as_part(then_list)
        index += 1
        else_list = tl.CollectiveElement(tl.CE_BRACKET, lf, None)
        while index < len(parent) and not tl.identifier_of(parent[index], ";"):
            else_list.append(parent[index])
            index += 1
        else_expr = self.parse_as_part(else_list)
        ife = ast.IfExpr(cond, then_expr, else_expr, lf)
        builder.add_node(ife)
        if index < len(parent):  # last loop terminated by a ';', add an eol
            self.process_eol(parent, index, builder, lf)
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

    def process_break(self, p, i, builder: ab.AstBuilder, lf):
        builder.add_node(ast.BreakStmt(lf))

    def process_continue(self, p, i, builder: ab.AstBuilder, lf):
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
            while not tl.identifier_of(parent[index], ";"):
                bracket.append(parent[index])
                index += 1
            content = self.parse_as_part(bracket)
        builder.add_node(ast.RequireStmt(content, lf))
        self.process_eol(parent, index, builder, lf)
        return index

    def process_import(self, parent: tl.CollectiveElement, index: int, builder: ab.AstBuilder, lf: tl.LineFile):
        file_atom: tl.AtomicElement = parent[index + 1]
        file_tk: tl.StrToken = file_atom.atom
        includes: tl.CollectiveElement = parent[index + 2]
        included_block = self.parse_as_block(includes)
        builder.add_node(ast.ImportStmt(file_tk.value, included_block, lf))

        return index + 2

    def process_export(self, parent: tl.CollectiveElement, index: int, builder: ab.AstBuilder, lf: tl.LineFile):
        index += 1
        ele = parent[index]
        if tl.is_brace(ele):
            block = self.parse_as_block(ele)
            builder.add_node(ast.ExportStmt(block, lf))
        elif isinstance(ele, tl.AtomicElement) and isinstance(ele.atom, tl.IdToken):
            block = ast.BlockStmt(lf)
            line = ast.Line(lf)
            line.parts.append(ast.NameNode(ele.atom.identifier, lf))
            block.lines.append(line)
            builder.add_node(ast.ExportStmt(block, lf))
        else:
            raise errs.TplCompileError("Invalid export. ", lf)

        return index

    def process_struct(self, parent: tl.CollectiveElement, index: int, builder: ab.AstBuilder, lf: tl.LineFile):
        name_ele = parent[index + 1]
        body_ele = parent[index + 2]

        if not (isinstance(name_ele, tl.AtomicElement) and
                isinstance(name_ele.atom, tl.IdToken) and
                tl.is_brace(body_ele)):
            raise errs.TplSyntaxError("Invalid struct syntax. ", lf)

        name = name_ele.atom.identifier
        body = self.parse_as_block(body_ele)
        builder.add_node(ast.StructStmt(name, body, lf))

        return index + 2

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
                if token.value in self.float_literals:
                    pos = self.float_literals[token.value]
                else:
                    pos = len(self.literal_bytes)
                    self.literal_bytes.extend(util.float_to_bytes(token.value))
                builder.add_node(ast.FloatLiteral(pos, lf))
            elif isinstance(token, tl.CharToken):
                if token.char in self.char_literals:
                    pos = self.char_literals[token.char]
                else:
                    pos = len(self.literal_bytes)
                    self.literal_bytes.extend(util.char_to_bytes(token.char))
                builder.add_node(ast.CharLiteral(pos, lf))
            elif isinstance(token, tl.StrToken):
                if token.value in self.str_literals:
                    pos = self.str_literals[token.value]
                else:
                    pos = len(self.literal_bytes)
                    self.literal_bytes.extend(util.string_to_bytes(token.value))
                builder.add_node(ast.StringLiteral(pos, lf))
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
                elif symbol in self.special_binary:
                    node_class = self.special_binary[symbol]
                    builder.add_node(node_class(lf))
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
                    if is_call_obj(prob_call_obj):
                        args = self.parse_as_line(ele)
                        call_obj = builder.remove_last()
                        call = ast.FunctionCall(call_obj, args, lf)
                        builder.add_node(call)
                        return index + 1
                parenthesis = self.parse_as_part(ele)
                builder.add_node(parenthesis)
            elif ele.is_sqr_bracket():
                lf = ele.lf
                if index > 0:
                    prob_call_obj = parent[index - 1]
                    if is_call_obj(prob_call_obj):
                        args = self.parse_as_line(ele)
                        call_obj = builder.remove_last()
                        call = ast.IndexingExpr(call_obj, args, lf)
                        builder.add_node(call)
                        return index + 1
        else:
            raise Exception("Unexpected error. ")

        return index + 1


UNARY_LEADING = {
    ";", ":", "=", "->", ".", ","
}


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


def is_call_obj(prob_call_obj: tl.Element) -> bool:
    return (isinstance(prob_call_obj, tl.AtomicElement) and is_call(prob_call_obj.atom)) or \
           (isinstance(prob_call_obj, tl.CollectiveElement) and (
                       prob_call_obj.is_sqr_bracket() or prob_call_obj.is_bracket()))
