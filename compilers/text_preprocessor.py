import os
import compilers.tokens_lib as tl
import compilers.errors as errs
import compilers.tokenizer as tkn


class Macro:
    def __init__(self, body, lf):
        self.lf = lf
        self.body = body


class SimpleMacro(Macro):
    def __init__(self, body, lf):
        super().__init__(body, lf)

    def __str__(self):
        return str(self.body)


class CallMacro(Macro):
    def __init__(self, params: list, body, lf):
        super().__init__(body, lf)

        self.params = params

    def __str__(self):
        return f"{self.params} {self.body}"


class MacroEnv:
    def __init__(self):
        self.macros = {}
        self.export_names = set()

    def add_macro(self, name: str, macro: Macro, lf):
        if name in self.macros:
            raise errs.TplMacroError(f"Macro '{name}' already defined in this scope. ", lf)
        self.macros[name] = macro

    def is_macro(self, name):
        return name in self.macros

    def get_macro(self, name) -> Macro:
        return self.macros[name]

    def add_export(self, name):
        self.export_names.add(name)


def get_name_list(lst: tl.CollectiveElement) -> list:
    res = []
    for part in lst:
        if isinstance(part, tl.AtomicElement) and \
                isinstance(part.atom, tl.IdToken) and \
                part.atom.identifier.isidentifier():
            res.append(part.atom.identifier)
        else:
            raise errs.TplSyntaxError("Macro param list must all be identifiers. ")
    return res


class FileTextPreprocessor:
    def __init__(self, tokens: tl.CollectiveElement, pref: dict,
                 included_files: {} = None, macros: MacroEnv = None):
        self.root = tokens

        self.pref = pref  # should contain "tpc_path", "main_dir", "import_lang"
        self.included_files = included_files if included_files is not None else {}
        self.macros = macros if macros is not None else MacroEnv()

    def preprocess(self) -> tl.CollectiveElement:
        return self.process_block(self.root, None)

    def process_one(self, parent: tl.CollectiveElement, index: int, result_parent: tl.CollectiveElement) -> int:
        ele = parent[index]
        if isinstance(ele, tl.AtomicElement):
            if isinstance(ele.atom, tl.IdToken):
                symbol = ele.atom.identifier
                lf = ele.atom.lfp
                if symbol == "macro":
                    index += 1
                    name_ele = parent[index]
                    if isinstance(name_ele, tl.AtomicElement) and isinstance(name_ele.atom, tl.IdToken):
                        name = name_ele.atom.identifier
                        index += 1
                        prob_params = parent[index]
                        if isinstance(prob_params, tl.CollectiveElement):
                            if prob_params.is_brace():  # macro name { ... }
                                macro = SimpleMacro(prob_params, lf)
                                self.macros.add_macro(name, macro, lf)
                                return index + 1
                            elif prob_params.is_bracket():  # macro name(...) ...
                                index += 1
                                body = parent[index]
                                if tl.is_brace(body):
                                    macro = CallMacro(get_name_list(prob_params), body, lf)
                                    self.macros.add_macro(name, macro, lf)
                                    return index + 1
                    raise errs.TplSyntaxError("Invalid macro syntax. ", lf)
                elif symbol == "exportmacro":
                    index += 1
                    exports = parent[index]
                    if tl.is_brace(exports):
                        for exp in exports:
                            if isinstance(exp, tl.AtomicElement) and isinstance(exp.atom, tl.IdToken):
                                if exp.atom.identifier != ",":
                                    self.macros.add_export(exp.atom.identifier)
                            else:
                                raise errs.TplSyntaxError("Invalid exportmacro syntax. ", lf)
                    elif isinstance(exports, tl.AtomicElement) and isinstance(exports.atom, tl.IdToken):
                        self.macros.add_export(exports.atom.identifier)
                    else:
                        raise errs.TplSyntaxError("Invalid exportmacro syntax. ", lf)
                    return index + 1

                elif symbol == "import":
                    index += 1
                    includes = parent[index]
                    if isinstance(includes, tl.AtomicElement):
                        self.import_one(includes.atom, result_parent, lf)
                    elif tl.is_brace(includes):
                        for inc in includes:
                            if isinstance(inc, tl.AtomicElement):
                                self.import_one(inc.atom, result_parent, lf)
                            else:
                                raise errs.TplSyntaxError("Invalid include. ", lf)
                    else:
                        raise errs.TplSyntaxError("Invalid include. ", lf)
                    return index + 1
                elif self.macros.is_macro(symbol):  # replace macro
                    macro = self.macros.get_macro(symbol)
                    if isinstance(macro, CallMacro):
                        index += 1
                        args = parent[index]
                        if not tl.is_bracket(args):
                            raise errs.TplSyntaxError("Invalid macro syntax. ", args.lfp)

                        arg_list = list_ify_macro_arg(args)

                        if len(arg_list) != len(macro.params):
                            raise errs.TplSyntaxError("Macro syntax arity mismatch. ", args.lfp)

                        body_with_arg = tl.CollectiveElement(tl.CE_BRACE, lf, None)
                        for body_ele in macro.body:
                            if isinstance(body_ele, tl.AtomicElement) and \
                                    isinstance(body_ele.atom, tl.IdToken) and \
                                    body_ele.atom.identifier in macro.params:
                                arg_index = macro.params.index(body_ele.atom.identifier)
                                body_with_arg.extend(arg_list[arg_index])
                            else:
                                body_with_arg.append(body_ele)
                        macro_res = self.process_block(body_with_arg, None)
                    else:
                        macro_res = self.process_block(macro.body, None)

                    result_parent.extend(macro_res)
                    return index + 1

            result_parent.append(ele)
        elif isinstance(ele, tl.CollectiveElement):
            res = self.process_block(ele, result_parent)
            result_parent.append(res)
        else:
            raise errs.TplError("Unexpected element. ", parent.lfp)

        return index + 1

    def import_one(self, include: tl.Token, result_parent, lf):
        if isinstance(include, tl.IdToken):
            # library import
            file = "{}{}lib{}{}.tp".format(self.pref["tpc_dir"],
                                           os.sep, os.sep, include.identifier)
        elif isinstance(include, tl.StrToken):
            # user import
            file = os.path.join(self.pref["main_dir"], include.value)
        else:
            raise errs.TplCompileError("Invalid include. ", lf)

        if not os.path.exists(file):
            raise errs.TplTokenizeError(f"File '{file}' does not exist. ", lf)

        if file not in self.included_files:
            lexer = tkn.FileTokenizer(file, self.pref["import_lang"])
            tokens = lexer.tokenize()

            self.included_files[file] = None  # make 'file' in 'self.included_files'

            module_macros = MacroEnv()
            txt_p = FileTextPreprocessor(tokens, self.pref, self.included_files, module_macros)
            processed_tks = txt_p.preprocess()

            self.included_files[file] = module_macros

            result_parent.append(tl.AtomicElement(tl.IdToken("import", lf), result_parent))
            result_parent.append(tl.AtomicElement(tl.StrToken(file, lf), result_parent))
            result_parent.append(processed_tks)

        module_macros = self.included_files[file]
        # print(file, module_macros.export_names)
        for en in module_macros.export_names:
            self.macros.add_macro(en, module_macros.get_macro(en), lf)

    def process_block(self, block: tl.CollectiveElement, result_parent: tl.CollectiveElement) -> tl.CollectiveElement:
        result = tl.CollectiveElement(block.ce_type, block.lfp, result_parent)
        i = 0
        while i < len(block):
            i = self.process_one(block, i, result)
        return result


def list_ify_macro_arg(args: tl.CollectiveElement) -> list:
    res = []
    cur = tl.CollectiveElement(tl.CE_BRACE, args.lfp, None)
    for arg in args:
        if tl.identifier_of(arg, ","):
            res.append(cur)
            cur = tl.CollectiveElement(tl.CE_BRACE, args.lfp, None)
        else:
            cur.append(arg)
    res.append(cur)
    return res
