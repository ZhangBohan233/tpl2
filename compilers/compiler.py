import compilers.tpa_producer as prod
import compilers.environment as en
import compilers.ast as ast
import compilers.types as typ
import compilers.errors as errs
import compilers.tokens_lib as tl

MAIN_FN_ERR_MSG = "Main function should be one of\n" + \
                  "main() int, main(void) int, main(args: char[][]) int, " + \
                  "main() void, main(void) void, main(args: char[][]) void"


class Compiler:
    def __init__(self, root: ast.BlockStmt, literals: bytes, main_file_path: str, optimize_level: int):
        self.root = root
        self.literals = literals
        self.main_path = main_file_path

        ast.set_optimize_level(optimize_level)

    def compile(self) -> str:
        manager = prod.Manager(self.literals)
        out = prod.TpaOutput(manager, is_global=True)
        ge = en.GlobalEnvironment()
        _init_compile_time_functions(ge)

        env = en.MainEnvironment(ge)

        self.root.compile(env, out)

        # call 'main'
        if not env.has_name("main"):
            raise errs.TplCompileError("Trash program without function 'main' cannot compile as executable. ")
        main_fp = env.get_type("main", tl.LF_COMPILER)
        if not isinstance(main_fp, typ.FunctionPlacer):
            raise errs.TplCompileError("Main must be a function")
        main_fn, main_addr = main_fp.get_only()
        if len(main_fn.param_types) == 0:
            out.generate(self.main_path)
        elif len(main_fn.param_types) == 1:
            if main_fn.param_types[0] == typ.TYPE_VOID:
                out.generate(self.main_path)
            elif main_fn.param_types[0] == typ.TYPE_STRING_ARR:
                out.generate(self.main_path, True)
            else:
                raise errs.TplCompileError(MAIN_FN_ERR_MSG)
        else:
            raise errs.TplCompileError(MAIN_FN_ERR_MSG)
        if main_fn.rtype != typ.TYPE_INT and main_fn.rtype != typ.TYPE_VOID:
            raise errs.TplCompileError(MAIN_FN_ERR_MSG)

        res = out.result()
        return "\n".join(res)


def _init_compile_time_functions(env: en.GlobalEnvironment):
    for func_t in ast.COMPILE_TIME_FUNCTIONS:
        env.define_const(func_t.name, func_t, tl.LF_COMPILER)
