import os
import compilers.tokens_lib as tl
import compilers.errors as errs
import compilers.tokenizer as tkn


class FileTextPreprocessor:
    def __init__(self, tokens: tl.CollectiveElement, pref: dict,
                 included_files: set = None):
        self.root = tokens

        self.pref = pref
        self.included_files = included_files if included_files is not None else set()

    def preprocess(self) -> tl.CollectiveElement:
        return self.process_block(self.root, None)

    def process_one(self, parent: tl.CollectiveElement, index: int, result_parent: tl.CollectiveElement) -> int:
        ele = parent[index]
        if isinstance(ele, tl.AtomicElement):
            if isinstance(ele.atom, tl.IdToken):
                symbol = ele.atom.identifier
                lf = ele.atom.lf
                if symbol == "import":
                    index += 1
                    includes = parent[index]
                    if isinstance(includes, tl.AtomicElement):
                        if isinstance(includes.atom, tl.IdToken):
                            # library import
                            file = "{}{}lib{}{}.tp".format(self.pref["tpc_path"],
                                                           os.sep, os.sep, includes.atom.identifier)
                        elif isinstance(includes.atom, tl.StrToken):
                            # user import
                            file = includes.atom.value
                        else:
                            raise errs.TplCompileError("Invalid include. ", lf)

                        if file not in self.included_files:
                            self.included_files.add(file)
                            lexer = tkn.FileTokenizer(file, self.pref["import_lang"])
                            tokens = lexer.tokenize()

                            txt_p = FileTextPreprocessor(tokens, self.pref, self.included_files)
                            processed_tks = txt_p.preprocess()

                            result_parent.append(ele)
                            result_parent.append(tl.AtomicElement(tl.StrToken(file, lf), result_parent))
                            result_parent.append(processed_tks)
                    else:
                        raise errs.TplCompileError("Invalid include. ", lf)
                    return index + 1

            result_parent.append(ele)
        elif isinstance(ele, tl.CollectiveElement):
            res = self.process_block(ele, result_parent)
            result_parent.append(res)
        else:
            raise errs.TplError("Unexpected element. ", parent.lf)

        return index + 1

    def process_block(self, block: tl.CollectiveElement, result_parent: tl.CollectiveElement):
        result = tl.CollectiveElement(block.ce_type, block.lf, result_parent)
        i = 0
        while i < len(block):
            i = self.process_one(block, i, result)
        return result
