class TpaError(Exception):
    def __init__(self, msg="", lf=None):
        super().__init__(msg)

        self.lf = lf

    def __str__(self):
        return super().__str__() + (str(self.lf) if self.lf else "")


class TplError(Exception):
    def __init__(self, msg="", lf=None):
        super().__init__(msg)

        self.lf = lf

    def __str__(self):
        return super().__str__() + (str(self.lf) if self.lf else "")


class TplSyntaxError(TplError):
    def __init__(self, msg="", lf=None):
        super().__init__(msg, lf)


class TplParseError(TplError):
    def __init__(self, msg="", lf=None):
        super().__init__(msg, lf)


class TplCompileError(TplError):
    def __init__(self, msg="", lf=None):
        super().__init__(msg, lf)


class TplTypeError(TplError):
    def __init__(self, msg="", lf=None):
        super().__init__(msg, lf)


class TplEnvironmentError(TplError):
    def __init__(self, msg="", lf=None):
        super().__init__(msg, lf)


class NotCompileAbleError(TplCompileError):
    def __init__(self, msg="", lf=None):
        super().__init__(msg, lf)
