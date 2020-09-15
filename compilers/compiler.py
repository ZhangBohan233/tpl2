import compilers.tpa_producer as prod
import compilers.environment as en
import compilers.ast as ast
import compilers.types as typ
import compilers.tokens_lib as tl


class Compiler:
    def __init__(self, root: ast.BlockStmt, literals: bytes, main_file_path: str, optimize_level: int):
        self.root = root
        self.literals = literals
        self.main_path = main_file_path

        ast.set_optimize_level(optimize_level)

    def compile(self) -> str:
        manager = prod.Manager(self.literals)
        out = prod.TpaOutput(manager, is_global=True)
        env = en.GlobalEnvironment()
        _init_compile_time_functions(env)

        self.root.compile(env, out)
        out.generate(self.main_path)
        res = out.result()

        return "\n".join(res)


def _init_compile_time_functions(env: en.GlobalEnvironment):
    for func_t in ast.COMPILE_TIME_FUNCTIONS:
        env.define_const(func_t.name, func_t, tl.LF_COMPILER)
