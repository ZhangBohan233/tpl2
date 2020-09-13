import compilers.tpa_producer as prod
import compilers.environment as en
import compilers.ast as ast
import compilers.types as typ
import compilers.tokens_lib as tl


class Compiler:
    def __init__(self, root: ast.BlockStmt, literals: bytes, main_file_path: str):
        self.root = root
        self.literals = literals
        self.main_path = main_file_path

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
    for name, tup in ast.COMPILE_TIME_FUNCTIONS.items():
        env.define_const(name, tup[1], tl.LF_COMPILER)
