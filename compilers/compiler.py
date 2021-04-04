import compilers.tpa_producer as prod
import compilers.environment as en
import compilers.ast as ast
import compilers.types as typ
import compilers.errors as errs
import compilers.tokens_lib as tl
import compilers.util as util

MAIN_FN_ERR_MSG = "Main function should be one of\n" + \
                  "main() int, main(void) int, main(args: char[][]) int, " + \
                  "main() void, main(void) void, main(args: char[][]) void"


class Compiler:
    def __init__(self, root: ast.BlockStmt, literals: bytes, str_lit_pos: dict,
                 main_file_path: str, optimize_level: int):
        self.root = root
        self.literals = literals
        self.str_lit_pos = str_lit_pos
        self.main_path = main_file_path
        self.optimize_level = optimize_level

        ast.set_optimize_level(optimize_level)

    def compile(self) -> str:
        manager = prod.Manager(self.literals, self.str_lit_pos, self.optimize_level)
        out = prod.TpaOutput(manager, is_global=True)
        ge = en.GlobalEnvironment()
        _init_compile_time_functions(ge, out)

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


def _init_compile_time_functions(env: en.GlobalEnvironment, tpa):
    for func_t in ast.COMPILE_TIME_FUNCTIONS:
        env.define_const(func_t.name, func_t, tl.LF_COMPILER)
    for name in typ.NATIVE_FUNCTIONS:
        func_id, func_type = typ.NATIVE_FUNCTIONS[name]
        fn_ptr = tpa.manager.allocate_global(func_type)
        tpa.require_name(name, fn_ptr)
        env.define_function(name, func_type, fn_ptr, tl.LF_COMPILER)
