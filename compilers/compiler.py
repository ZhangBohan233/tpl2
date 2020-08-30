import compilers.errors as errs
import compilers.tpa_producer as prod
import compilers.environment as en
import compilers.ast as ast


class Compiler:
    def __init__(self, root: ast.BlockStmt, literals: bytes):
        self.root = root
        self.literals = literals

    def compile(self) -> str:
        manager = prod.Manager(self.literals)
        out = prod.TpaOutput(manager)
        env = en.GlobalEnvironment()

        self.root.compile(env, out)
        out.generate()
        res = out.result()

        return "\n".join(res)
