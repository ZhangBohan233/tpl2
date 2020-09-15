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
                 "optimize": 0, "no_lang": False, "tokens": False, "ast": False, "delete": False}
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg[0] == "-":
            if len(arg) == 1:
                print("Illegal syntax")
            elif arg[1:].lower() == "nl" or arg[1:].lower() == "-no-lang":
                args_dict["no_lang"] = True
            elif arg[1:].lower() == "del":
                args_dict["delete"] = True
            elif arg[1].lower() == "o":
                try:
                    op_level = int(arg[2:])
                    args_dict["optimize"] = op_level
                except ValueError:
                    print("Illegal optimize level")
            elif arg[1:].lower() == "tk" or arg[1:].lower() == "-tokens":
                args_dict["tokens"] = True
            elif arg[1:].lower() == "ast":
                args_dict["ast"] = True
            elif arg[1:].lower() == "tpa":
                args_dict["tpa_file"] = sys.argv[i + 1]
                i += 1
            elif arg[1:].lower() == "tpc":
                args_dict["tpc_file"] = sys.argv[i + 1]
                i += 1
            elif arg[1:].lower() == "tpe":
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
    t0 = time.time()

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

    parser = psr.Parser(processed_tks)
    fake_root = parser.parse()

    if args["optimize"] > 0:
        ast_opt = ast_o.AstOptimizer(fake_root, args["optimize"])
        fake_root = ast_opt.optimize()

    tree_pre = prep.AstPreprocessor(fake_root)
    root, literal = tree_pre.preprocess()

    if args["ast"]:
        print(root)
        print("========== End of AST ==========")

    compiler = cmp.Compiler(root, literal, src_abs_path, args["optimize"])
    # compiler.configs(optimize=args["optimize"])
    tpa_content = compiler.compile()

    tpc_name = args["tpc_file"]
    tpa_name = args["tpa_file"]
    tpe_name = args["tpe_file"]

    rem_file = [tpc_name, tpa_name]

    # with open(tpa_name, "r") as tpa_f:
    #     tpa_text = tpa_f.read()
    #     tpa_cmp = optimizer.TpaParser(tpa_text)

    # if args["optimize"] > 1:
    #     # print("Optimization currently unavailable")
    #     # exit(1)
    #     opt = optimizer.Optimizer(tpa_cmp)
    #     opt.optimize(args["optimize"])

    with open(tpa_name, "w") as tpa_file:
        tpa_file.write(tpa_content)

    tpc_cmp = tpc.TpcCompiler(tpa_name)
    tpc_cmp.compile(tpc_name)

    final_tpc_name = tpc_name

    if args["optimize"] > 0:
        opt = tpc_o.TpcOptimizer(tpc_name, args["optimize"])
        opt_file = replace_extension(tpc_name, ".o.tpc")
        rem_file.append(opt_file)
        opt.optimize(opt_file)

        final_tpc_name = opt_file

    tpe_cmp = tpc.TpeCompiler(final_tpc_name)
    tpe_cmp.compile(tpe_name)

    t1 = time.time()
    print("Compilation finished in {} seconds.".format(t1 - t0))

    if args["delete"]:
        for f in rem_file:
            os.remove(f)

