"""
tpl -> tpa -> tpc -> tpe

tpl: Trash Program Source File
tpa: Trash Program Assembly (Readable)
tpc: Trash Program Compiled Assembly (Readable)
tpe: Trash Program Executable
"""

import os
import sys
import time
import compilers.tokens_lib as tl
import compilers.compiler as cmp
import compilers.tp_parser as psr
import compilers.tokenizer as lex
import compilers.text_preprocessor as txt_prep
import compilers.tpc_compiler as tpc
import compilers.tpc_optimizer as tpc_o
import compilers.ast_preprocessor as prep
import compilers.ast_optimizer as ast_o


TPC_NAME = "tpc.py"


USAGE = """Usage: python tpc.py [flags] source target
    flags:
        -ast:            prints out the abstract syntax tree
        -nl, --no-lang   do not automatically import lang.tp
        -o<x>:           optimization level x
        -tk, --tokens    prints out the language tokens
"""


def parse_args():
    args_dict = {"py": sys.argv[0], "src_file": None, "tpc_file": None, "tpa_file": None, "tpe_file": None,
                 "optimize": 0, "no_lang": False, "tokens": False, "ast": False, "delete": False, "timer": False}
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg[0] == "-":
            flag = arg[1:].lower()
            if len(flag) == 0:
                print("Illegal syntax")
            elif flag == "nl" or flag == "-no-lang":
                args_dict["no_lang"] = True
            elif flag == "del":
                args_dict["delete"] = True
            elif arg[1].lower() == "o":
                try:
                    op_level = int(arg[2:])
                    args_dict["optimize"] = op_level
                except ValueError:
                    print("Illegal optimize level")
            elif flag == "tk" or flag == "-tokens":
                args_dict["tokens"] = True
            elif flag == "ast":
                args_dict["ast"] = True
            elif flag == "t" or flag == "-timer":
                args_dict["timer"] = True
            elif flag == "tpa":
                args_dict["tpa_file"] = sys.argv[i + 1]
                i += 1
            elif flag == "tpc":
                args_dict["tpc_file"] = sys.argv[i + 1]
                i += 1
            elif flag == "tpe":
                args_dict["tpe_file"] = sys.argv[i + 1]
                i += 1
            else:
                print("Unknown flag '{}'".format(arg))
        elif args_dict["src_file"] is None:
            args_dict["src_file"] = arg
        else:
            print("Unexpected argument")
        i += 1

    if args_dict["src_file"] is None:
        print(USAGE)
        return None
    if not args_dict["src_file"].endswith(".tp"):
        print("Source file must be a Trash Program (*.tp). ")
        return None

    if args_dict["tpa_file"] is None:
        args_dict["tpa_file"] = replace_extension(args_dict["src_file"], ".tpa")
    if args_dict["tpc_file"] is None:
        args_dict["tpc_file"] = replace_extension(args_dict["tpa_file"], ".tpc")
    if args_dict["tpe_file"] is None:
        args_dict["tpe_file"] = replace_extension(args_dict["tpc_file"], ".tpe")
    return args_dict


def get_tpc_dir():
    """
    Returns the absolute path of tpc.py

    :return:
    """
    return os.path.dirname(os.path.abspath(__file__))


def replace_extension(orig_name: str, ext: str):
    return orig_name[:orig_name.rfind(".")] + ext


if __name__ == '__main__':
    t_begin = time.time()

    args = parse_args()
    if args is None:
        exit(1)

    # with open(args["src_file"], "r") as rf:
    src_abs_path = os.path.abspath(args["src_file"])
    lexer = lex.FileTokenizer(src_abs_path, not args["no_lang"])
    tokens = lexer.tokenize()

    if args["tokens"]:
        print(tokens)

    txt_p = txt_prep.FileTextPreprocessor(tokens,
                                          {"tpc_dir": get_tpc_dir(),
                                           "main_dir": os.path.dirname(src_abs_path),
                                           "import_lang": not args["no_lang"]})
    processed_tks = txt_p.preprocess()

    t_preprocess_end = time.time()

    parser = psr.Parser(processed_tks)
    fake_root = parser.parse()

    if args["optimize"] > 0:
        ast_opt = ast_o.AstOptimizer(fake_root, args["optimize"])
        fake_root = ast_opt.optimize()

    tree_pre = prep.AstPreprocessor(fake_root)
    root, literal, str_lit_pos = tree_pre.preprocess()

    t_parse_end = time.time()

    if args["ast"]:
        print(root)
        print("========== End of AST ==========")

    compiler = cmp.Compiler(root, literal, str_lit_pos, src_abs_path, args["optimize"])
    tpa_content = compiler.compile()

    tpc_name = args["tpc_file"]
    tpa_name = args["tpa_file"]
    tpe_name = args["tpe_file"]

    rem_file = [tpc_name, tpa_name]

    with open(tpa_name, "w") as tpa_file:
        tpa_file.write(tpa_content)

    t_compile_end = time.time()

    tpc_cmp = tpc.TpcCompiler(tpa_name)
    tpc_cmp.compile(tpc_name)

    final_tpc_name = tpc_name

    if args["optimize"] > 0:
        opt = tpc_o.TpcOptimizer(tpc_name, args["optimize"])
        opt_file = replace_extension(tpc_name, ".o.tpc")
        rem_file.append(opt_file)
        opt.optimize(opt_file)

        final_tpc_name = opt_file

    t_tpc_end = time.time()

    tpe_cmp = tpc.TpeCompiler(final_tpc_name)
    tpe_cmp.compile(tpe_name)

    t_end = time.time()

    if args["timer"]:
        print(f"Time used: \n"
              f"preprocess: {round(t_preprocess_end - t_begin, 4)} s, "
              f"parse: {round(t_parse_end - t_preprocess_end, 4)} s, "
              f"compile: {round(t_compile_end - t_preprocess_end, 4)} s, "
              f"tpc compile: {round(t_tpc_end - t_compile_end, 4)} s, "
              f"tpe compile: {round(t_end - t_tpc_end, 4)} s.")

    print(f"Compilation finished in {round(t_end - t_begin, 4)} seconds.")

    if args["delete"]:
        for f in rem_file:
            os.remove(f)

