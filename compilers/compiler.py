import compilers.tpa_producer as prod
import compilers.environment as en
import compilers.ast as ast


class Compiler:
    def __init__(self, root: ast.BlockStmt, literals: bytes, main_file_path: str):
        self.root = root
        self.literals = literals
        self.main_path = main_file_path

    def compile(self) -> str:
        manager = prod.Manager(self.literals)
        out = prod.TpaOutput(manager, is_global=True)
        env = en.GlobalEnvironment()

        self.root.compile(env, out)
        out.generate(self.main_path)
        res = out.result()

        return "\n".join(res)
