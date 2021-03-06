class TpaError(Exception):
    def __init__(self, msg="", lfp=None):
        super().__init__(msg)

        self.lfp = lfp

    def __str__(self):
        return super().__str__() + (str(self.lfp) if self.lfp else "")


class TplError(Exception):
    def __init__(self, msg="", lfp=None):
        super().__init__(msg)

        self.lfp = lfp

    def __str__(self):
        return super().__str__() + (str(self.lfp) if self.lfp else "")


class TplTokenizeError(TplError):
    def __init__(self, msg="", lf=None):
        super().__init__(msg, lf)


class TplSyntaxError(TplError):
    def __init__(self, msg="", lf=None):
        super().__init__(msg, lf)


class TplMacroError(TplError):
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
