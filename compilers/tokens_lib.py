ARITH_BINARY = {"+", "-", "*", "/", "%"}
BITWISE_BINARY = {"&", "|", "^", ">>", "<<", ">>>"}
ARITH_BINARY_ASS = {"+=", "-=", "*=", "/=", "%="}
BITWISE_BINARY_ASS = {"&=", "|=", "^=", ">>=", "<<=", ">>>="}
LOGICAL_BINARY = {"<", ">", "==", "!=", "<=", ">="}
LAZY_BINARY = {"and", "or"}
ARITH_UNARY = {"-", "*", "&"}
LOGICAL_UNARY = {"not"}
SYMBOLS = {"{", "}", "[", "]", "(", ")", ".", "$", ",", ";", ":"}
OTHERS = {"=", "->", ":=", "++", "--"}

RESERVED = {"as", "break", "case", "cond", "const", "continue", "del", "do", "else",
            "export", "exportmacro", "fallthrough", "fn", "for",
            "if", "import", "macro", "new", "require", "return", "struct", "switch", "then", "var", "while", "yield"}

ALL_BINARY = set.union(
    ARITH_BINARY,
    BITWISE_BINARY,
    ARITH_BINARY_ASS,
    BITWISE_BINARY_ASS,
    LOGICAL_BINARY,
    OTHERS
)

ALL = set.union(
    ARITH_BINARY,
    BITWISE_BINARY,
    ARITH_BINARY_ASS,
    BITWISE_BINARY_ASS,
    LOGICAL_BINARY,
    LAZY_BINARY,
    ARITH_UNARY,
    LOGICAL_UNARY,
    SYMBOLS,
    OTHERS,
    RESERVED
)


class LineFile:
    def __init__(self, file_name: str, line: int):
        self.file_name = file_name
        self.line = line

    def __str__(self):
        return "In file '" + self.file_name + "', at line " + str(self.line) + "."


LF_TOKENIZER = LineFile("Tokenizer", 0)
LF_PARSER = LineFile("Parser", 0)
LF_COMPILER = LineFile("Compiler", 0)


class Token:
    def __init__(self, lf):
        self.lf: LineFile = lf

    def __repr__(self):
        return self.__str__()


class CharToken(Token):
    def __init__(self, char: str, lf):
        super().__init__(lf)

        self.char = char

    def __str__(self):
        return "Id{" + self.char + "}"


class IntToken(Token):
    def __init__(self, v: str, lf):
        super().__init__(lf)

        self.value = int(v)

    def __str__(self):
        return "Int{" + str(self.value) + "}"


class ByteToken(Token):
    def __init__(self, v: str, lf):
        super().__init__(lf)

        self.value = int(v)

    def __str__(self):
        return "Byte{" + str(self.value) + "}"


class FloatToken(Token):
    def __init__(self, v: str, lf):
        super().__init__(lf)

        self.value = float(v)

    def __str__(self):
        return "Float{" + str(self.value) + "}"


class IdToken(Token):
    def __init__(self, v: str, lf):
        super().__init__(lf)

        self.identifier = v

    def __str__(self):
        return "Id{" + self.identifier + "}"


class StrToken(Token):
    def __init__(self, v: str, lf):
        super().__init__(lf)

        self.value = v

    def __str__(self):
        return "Str{" + self.value + "}"


CE_BRACKET = 1
CE_BRACE = 2
CE_SQR_BRACKET = 3
CE_ARROW_BRACKET = 4


class Element:
    def __init__(self, parent):
        self.parent: CollectiveElement = parent

    def __repr__(self):
        return self.__str__()


class AtomicElement(Element):
    def __init__(self, atom: Token, parent):
        super().__init__(parent)

        self.atom = atom

    def __str__(self):
        return str(self.atom)


class CollectiveElement(Element):
    def __init__(self, ce_type: int, lf: LineFile, parent):
        super().__init__(parent)

        self.ce_type = ce_type
        self.lf = lf
        self.children = []

    def __getitem__(self, item):
        return self.children[item]

    def __setitem__(self, key, value):
        self.children[key] = value

    def __len__(self):
        return len(self.children)

    def append(self, value):
        self.children.append(value)

    def extend(self, other):
        for e in other:
            self.append(e)

    def name(self):
        if self.ce_type == CE_BRACE:
            return "Brace"
        if self.ce_type == CE_SQR_BRACKET:
            return "SqrBracket"
        if self.ce_type == CE_BRACKET:
            return "Bracket"
        if self.ce_type == CE_ARROW_BRACKET:
            return "ArrowBracket"
        return "???"

    def is_bracket(self):
        return self.ce_type == CE_BRACKET

    def is_brace(self):
        return self.ce_type == CE_BRACE

    def is_sqr_bracket(self):
        return self.ce_type == CE_SQR_BRACKET

    def is_arrow_bracket(self):
        return self.ce_type == CE_ARROW_BRACKET

    def __str__(self):
        return self.name() + str(self.children)


def is_brace(ele: Element):
    return isinstance(ele, CollectiveElement) and ele.is_brace()


def is_bracket(ele: Element):
    return isinstance(ele, CollectiveElement) and ele.is_bracket()


def is_arrow_bracket(ele: Element):
    return isinstance(ele, CollectiveElement) and ele.is_arrow_bracket()


def identifier_of(ele: Element, target: str) -> bool:
    return isinstance(ele, AtomicElement) and isinstance(ele.atom, IdToken) and ele.atom.identifier == target
