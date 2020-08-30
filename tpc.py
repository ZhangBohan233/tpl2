"""
tpl -> tpa -> tpc

tpl: Trash Program Source File
tpa: Trash Program Assembly (Readable)
tpc: Trash Program Compiled Assembly
"""

import os
import sys
import time
import compilers.tokens_lib as tl
import compilers.compiler as cmp
import compilers.tp_parser as psr
import compilers.tokenizer as lex
import compilers.tpc_compiler as tpc
import compilers.ast_preprocessor as prep


SPL_NAME = "spl.py"


def get_spl_path():
    return os.path.dirname(os.path.abspath(__file__))


USAGE = """Usage: python tpc.py [flags] source target
    flags:
        -ast:            prints out the abstract syntax tree
        -nl, --no-lang   do not automatically import lang.tp
        -o<x>:           optimization level x
        -tk, --tokens    prints out the language tokens
"""


def parse_args():
    args_dict = {"py": sys.argv[0], "src_file": None, "tar_file": None, "optimize": 0, "no_lang": False,
                 "tokens": False, "ast": False}
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg[0] == "-":
            if len(arg) == 1:
                print("Illegal syntax")
            elif arg[1:].lower() == "nl" or arg[1:].lower() == "-no-lang":
                args_dict["no_lang"] = True
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
            else:
                print("Unknown flag '{}'".format(arg))
        elif args_dict["src_file"] is None:
            args_dict["src_file"] = arg
        elif args_dict["tar_file"] is None:
            args_dict["tar_file"] = arg
        else:
            print("Unexpected argument")
        i += 1
    return args_dict


if __name__ == '__main__':
    t0 = time.time()

    args = parse_args()
    if not args["src_file"] or not args["tar_file"]:
        print(USAGE)

    # with open(args["src_file"], "r") as rf:
    lexer = lex.FileTokenizer(args["src_file"], not args["no_lang"])
    tokens: tl.CollectiveElement = lexer.tokenize()

    if args["tokens"]:
        print(tokens)

    parser = psr.Parser(tokens)
    root, literal = parser.parse()

    # preprocessor = prep.Preprocessor()
    # preprocessor.preprocess(root)

    # tree_optimizer = aso.AstOptimizer(root, parser, args["optimize"])
    # tree_optimizer.optimize()

    if args["ast"]:
        print(root)
        print("========== End of AST ==========")

    compiler = cmp.Compiler(root, literal)
    # compiler.configs(optimize=args["optimize"])
    tpa_content = compiler.compile()

    tar_name = args["tar_file"]
    pure_name = tar_name[:tar_name.rfind(".")]
    tpa_name = pure_name + ".tpa"

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

    tpa_cmp = tpc.TpcCompiler(tpa_name)
    tpa_cmp.compile(tar_name)

    t1 = time.time()
    print("Compilation finished in {} seconds.".format(t1 - t0))

