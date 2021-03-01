import os
import compilers.errors as errs
import compilers.util as util
import compilers.tokens_lib as tl


ESCAPES = {
    '0': '\0',
    'b': '\b',
    'f': '\f',
    'n': '\n',
    'r': '\r',
    't': '\t'
}


class FileTokenizer:
    def __init__(self, file_name: str, import_lang: bool):
        self.file_name = file_name
        self.import_lang = import_lang
        self.tokens = []
        self.in_doc = False

    def tokenize(self) -> tl.CollectiveElement:
        utf8bom = False
        if os.stat(self.file_name).st_size >= 3:
            with open(self.file_name, "rb") as test:
                if test.read(3) == b'\xef\xbb\xbf':
                    utf8bom = True
        if utf8bom:
            rf = open(self.file_name, "r", encoding="utf-8-sig")
        else:
            rf = open(self.file_name, "r")
        line = rf.readline()
        line_num = 1
        while line:
            lf = tl.LineFile(self.file_name, line_num)
            self.proceed_line(line, lf)
            line = rf.readline()
            line_num += 1
        rf.close()
        return self.make_root_tree()

    def make_root_tree(self):
        root = tl.CollectiveElement(tl.CE_BRACE, tl.LF_TOKENIZER, None)
        cur_active = root
        for i in range(len(self.tokens)):
            cur_active = self.make_tree(cur_active, i)
        return root

    def make_tree(self, cur_active: tl.CollectiveElement, index: int) -> tl.CollectiveElement:
        tk = self.tokens[index]
        if isinstance(tk, tl.IdToken):
            symbol = tk.identifier
            if symbol == "(":
                return tl.CollectiveElement(tl.CE_BRACKET, tk.lf, cur_active)
            if symbol == "[":
                return tl.CollectiveElement(tl.CE_SQR_BRACKET, tk.lf, cur_active)
            if symbol == "{":
                return tl.CollectiveElement(tl.CE_BRACE, tk.lf, cur_active)
            if symbol == ")":
                if cur_active.ce_type == tl.CE_BRACKET:
                    cur_active.parent.append(cur_active)
                    return cur_active.parent
                else:
                    raise errs.TplSyntaxError("Parenthesis does not close. ", tk.lf)
            if symbol == "]":
                if cur_active.ce_type == tl.CE_SQR_BRACKET:
                    cur_active.parent.append(cur_active)
                    return cur_active.parent
                else:
                    raise errs.TplSyntaxError("Parenthesis does not close. ", tk.lf)
            if symbol == "}":
                if cur_active.ce_type == tl.CE_BRACE:
                    cur_active.parent.append(cur_active)
                    return cur_active.parent
                else:
                    raise errs.TplSyntaxError("Parenthesis does not close. ", tk.lf)
            if symbol == "<":
                if has_closing_arrow(self.tokens, index):
                    return tl.CollectiveElement(tl.CE_ARROW_BRACKET, tk.lf, cur_active)
            if symbol == ">":
                if tl.is_arrow_bracket(cur_active):
                    cur_active.parent.append(cur_active)
                    return cur_active.parent

        cur_active.append(tl.AtomicElement(tk, cur_active))
        return cur_active

    def proceed_line(self, content: str, lf):
        in_str = False
        length = len(content)
        literal = ""
        non_literal = ""
        i = 0
        while i < length:
            ch = content[i]
            if self.in_doc:
                if i < length - 1 and ch == '*' and content[i + 1] == '/':
                    # exit doc
                    self.in_doc = False
                    i += 2
            else:
                if in_str:
                    if ch == '"':
                        in_str = False
                        self.tokens.append(tl.StrToken(literal, lf))
                        literal = ""
                    else:
                        literal += ch
                else:
                    if i < length - 1 and ch == '/' and content[i + 1] == '*':
                        # enter doc
                        self.in_doc = True
                        i += 1
                    elif i < length - 1 and ch == '/' and content[i + 1] == '/':
                        # enter comment, end of this line
                        if len(non_literal) > 2:
                            self.line_tokenize(non_literal[0:len(non_literal) - 2], lf)
                            non_literal = ""
                        break
                    elif ch == '"':
                        # enter string literal
                        in_str = True
                        self.line_tokenize(non_literal, lf)
                        non_literal = ""
                    elif ch == '\'':
                        # enter char literal
                        if i < length - 2 and content[i + 2] == '\'':
                            # normal char
                            self.line_tokenize(non_literal, lf)
                            non_literal = ""
                            self.tokens.append(tl.CharToken(content[i + 1], lf))
                            i += 2
                        elif i < length - 3 and content[i + 3] == '\'' and content[i + 1] == '\\':
                            # escape char
                            self.line_tokenize(non_literal, lf)
                            non_literal = ""
                            escaped = content[i + 2]
                            if escaped == '\\':
                                self.tokens.append(tl.CharToken('\\', lf))
                            elif escaped in ESCAPES:
                                self.tokens.append(tl.CharToken(ESCAPES[escaped], lf))
                            else:
                                raise errs.TplSyntaxError("Invalid escape '\\" + escaped + "'. ", lf)
                            i += 3
                        else:
                            raise errs.TplSyntaxError("Char literal must contain exactly one symbol. ", lf)
                    else:
                        non_literal += ch
            i += 1

        if len(non_literal) > 0:
            self.line_tokenize(non_literal, lf)

    def line_tokenize(self, content: str, lf):
        lst = normalize_line(content)
        length = len(lst)
        i = 0
        while i < length:
            s = lst[i]
            if is_int(s):
                if i < length - 2 and lst[i + 1] == "." and is_int(lst[i + 2]):
                    self.tokens.append(tl.FloatToken(s + "." + lst[i + 2], lf))
                    i += 2
                elif i < length - 1 and lst[i + 1] == "b":
                    self.tokens.append(tl.ByteToken(s, lf))  # 1b
                    i += 1
                elif i < length - 1 and lst[i + 1] == "f":
                    self.tokens.append(tl.FloatToken(s, lf))  # situation like 1f (== 1.0)
                    i += 1
                else:
                    self.tokens.append(tl.IntToken(s, lf))
            # elif s == "\n":
            #     self.tokens.append(tl.IdToken(s, lf))
            elif s.isidentifier():
                self.tokens.append(tl.IdToken(s, lf))
            elif s in tl.ALL:
                self.tokens.append(tl.IdToken(s, lf))
            i += 1


NOT_INT = 0
INT = 1
BYTE = 2
FLOAT = 3


def is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False


def normalize_line(line: str):
    lst = []
    if len(line) > 0:
        last = line[0]
        res = last
        for i in range(1, len(line)):
            cur = line[i]
            if not concatenate_able(last, cur):
                lst.append(res)
                res = ""
            res += cur
            last = cur
        lst.append(res)
    return lst


# char types

DIGIT = 1
LETTER = 2
L_BRACE = 3
R_BRACE = 4
L_BRACKET = 5
R_BRACKET = 6
L_SQR_BRACKET = 7
R_SQR_BRACKET = 8
EOL = 9
NEW_LINE = 10
GT = 11
LT = 12
EQ = 13
AND = 14
OR = 15
XOR = 16
DOT = 17
COMMA = 18
UNDERSCORE = 19
NOT = 20
PLUS = 21
MINUS = 22
OTHER_ARITHMETIC = 23
TYPE = 24
ESCAPE = 25
QUESTION = 26
UNDEFINED = 0

SELF_CONCATENATE = {
    DIGIT, LETTER, GT, EQ, LT, UNDERSCORE, PLUS, MINUS, TYPE
}

CROSS_CONCATENATE = {
    (LETTER, UNDERSCORE),
    (UNDERSCORE, LETTER),
    (DIGIT, UNDERSCORE),
    (UNDERSCORE, DIGIT),
    (MINUS, GT),
    (LT, MINUS),
    (LETTER, DIGIT),
    (GT, EQ),
    (LT, EQ),
    (NOT, EQ),
    (PLUS, EQ),
    (MINUS, EQ),
    (OTHER_ARITHMETIC, EQ),
    (TYPE, EQ),
    (ESCAPE, L_SQR_BRACKET),
    (LETTER, QUESTION),
    (DIGIT, QUESTION)
}

CHAR_TYPE_TABLE = {
    '{': L_BRACE,
    '}': R_BRACE,
    '(': L_BRACKET,
    ')': R_BRACKET,
    '[': L_SQR_BRACKET,
    ']': R_SQR_BRACKET,
    ';': EOL,
    '\n': NEW_LINE,
    '>': GT,
    '<': LT,
    '=': EQ,
    '&': AND,
    '|': OR,
    '^': XOR,
    '.': DOT,
    ',': COMMA,
    '_': UNDERSCORE,
    '!': NOT,
    '+': PLUS,
    '-': MINUS,
    '*': OTHER_ARITHMETIC, '/': OTHER_ARITHMETIC, '%': OTHER_ARITHMETIC,
    ':': TYPE,
    '\\': ESCAPE,
    '?': QUESTION,
}


def char_type(ch: str):
    if ch.isdigit():
        return DIGIT
    if ch.isalpha():
        return LETTER
    elif ch in CHAR_TYPE_TABLE:
        return CHAR_TYPE_TABLE[ch]
    else:
        return UNDEFINED


def concatenate_able(ch1: str, ch2: str) -> bool:
    lt = char_type(ch1)
    rt = char_type(ch2)
    return (lt == rt and lt in SELF_CONCATENATE) or \
           (lt, rt) in CROSS_CONCATENATE


def has_closing_arrow(tokens: list, left_arr_index: int) -> bool:
    for i in range(left_arr_index + 1, len(tokens)):
        tk = tokens[i]
        if isinstance(tk, tl.IdToken):
            if tk.identifier == ">":
                return True
            elif tk.identifier == ";":
                return False
        elif (isinstance(tk, tl.StrToken) or
              isinstance(tk, tl.IntToken) or
              isinstance(tk, tl.ByteToken) or
              isinstance(tk, tl.CharToken) or
              isinstance(tk, tl.FloatToken)):
            return False
    return False
