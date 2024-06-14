# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import builtins
import types
from pyflakes import api as pyflakes_api
from pyflakes import messages

from pylsp import hookimpl, lsp

# for variable parsing
import ast

# Pyflakes messages that should be reported as Errors instead of Warns
PYFLAKES_ERROR_MESSAGES = (
    messages.UndefinedName,
    messages.UndefinedExport,
    messages.UndefinedLocal,
    messages.DuplicateArgument,
    messages.FutureFeatureNotDefined,
    messages.ReturnOutsideFunction,
    messages.YieldOutsideFunction,
    messages.ContinueOutsideLoop,
    messages.BreakOutsideLoop,
    messages.TwoStarredExpressions,
)

# List of Patch functions  
CUSTOM_VALID_FUNCTIONS = []


# Gets all Python key words and functions
PYTHON_KEY_WORDS = [name for name, obj in vars(builtins).items() 
                          if not isinstance(obj, types.BuiltinFunctionType)]
PYTHON_FUNCTIONS =  [name for name, obj in vars(builtins).items() 
                          if isinstance(obj, types.BuiltinFunctionType)]

@hookimpl
def pylsp_lint(workspace, document):
    for func in document._config.settings().get("apiData"):
        CUSTOM_VALID_FUNCTIONS.append(func)
    with workspace.report_progress("lint: pyflakes"):
        reporter = PyflakesDiagnosticReport(document.lines)
        pyflakes_api.check(
            document.source.encode("utf-8"), document.path, reporter=reporter
        )
        return reporter.diagnostics


class PyflakesDiagnosticReport:
    def __init__(self, lines):
        self.lines = lines
        self.diagnostics = []
        self.source = '\n'.join([str(item) for item in lines])

    def unexpectedError(self, _filename, msg):  # pragma: no cover
        err_range = {
            "start": {"line": 0, "character": 0},
            "end": {"line": 0, "character": 0},
        }
        self.diagnostics.append(
            {
                "source": "pyflakes",
                "range": err_range,
                "message": msg,
                "severity": lsp.DiagnosticSeverity.Error,
            }
        )

    def syntaxError(self, _filename, msg, lineno, offset, text):
        # We've seen that lineno and offset can sometimes be None
        lineno = lineno or 1
        offset = offset or 0
        # could be None if the error is due to an invalid encoding
        # see e.g. https://github.com/python-lsp/python-lsp-server/issues/429
        text = text or ""

        err_range = {
            "start": {"line": lineno - 1, "character": offset},
            "end": {"line": lineno - 1, "character": offset + len(text)},
        }
        self.diagnostics.append(
            {
                "source": "pyflakes",
                "range": err_range,
                "message": msg,
                "severity": lsp.DiagnosticSeverity.Error,
            }
        )

    def flake(self, message):
        """Get message like <filename>:<lineno>: <msg>"""
        err_range = {
            "start": {"line": message.lineno - 1, "character": message.col},
            "end": {
                "line": message.lineno - 1,
                "character": len(self.lines[message.lineno - 1]),
            },
        }

        severity = lsp.DiagnosticSeverity.Warning
        for message_type in PYFLAKES_ERROR_MESSAGES:
            if isinstance(message, message_type):
                severity = lsp.DiagnosticSeverity.Error
                break

        # determines if two strings (a and b) are one off
        # Comes from here: https://stackoverflow.com/a/28665369
        def almost_equal(a, b):
            if (len(a) == len(b)):
                count = 0
                for x, y in zip(a, b):
                    count += x != y
                    if count == 2:
                        return False
                return True
            if abs(len(a) - len(b)) > 1: return False
            if len(a) < len(b):
                a, b = b, a
            it1 = iter(a)
            it2 = iter(b)
            count_diffs = 0
            c1 = next(it1, None)
            c2 = next(it2, None)
            while True:
                if c1 != c2:
                    if count_diffs: return False
                    count_diffs = 1
                    c1 = next(it1)
                else:
                    try:
                        c1 = next(it1)
                        c2 = next(it2)
                    except StopIteration: return True
        


        #Gets rid of error message because ruff provides default Python message.
        msg = ""
        errorName = message.message_args[0]
        if (message_type == messages.UndefinedName):
            #First we determine if the error is a valid custom funcion in which case we throw no error
            if (errorName in set(CUSTOM_VALID_FUNCTIONS)):
                return
            
            #Now determine if the error happens at a function (by parsing for parentheses)
            isFun = False
            locOfParen = self.lines[message.lineno - 1].find(errorName) + len(errorName)
            if (locOfParen < len(self.lines[message.lineno - 1]) and self.lines[message.lineno - 1][locOfParen] == "("):
                isFun = True

            #Now parse the syntax tree to get all customly defined variable/function names in the source code
            root = ast.parse(self.source)
            funs = list({
                node.value.func.id: None for node in ast.walk(root)
                if isinstance(node, ast.Expr) and hasattr(node, 'value') and isinstance(node.value, ast.Call) and hasattr(node.value.func, 'id')
            })
            vars = list({
                node.id: None for node in ast.walk(root)
                if isinstance(node, ast.Name)
            })
            vars = [i for i in vars if not i in set(funs)]

            #Then check if unassigned/undefined
            checkSet = funs if isFun else vars
            if (checkSet.count(errorName) <= 1):
                instructStr = "defining" if isFun else "assigning a value to"
                msg += "Try " + instructStr + " \'" + errorName + "\' before using it. "
            namesSet = set(checkSet).difference(set(CUSTOM_VALID_FUNCTIONS))
            namesSet.discard(errorName)

            #First check for misspelled builtin words
            for m in (CUSTOM_VALID_FUNCTIONS + PYTHON_FUNCTIONS if isFun else PYTHON_KEY_WORDS):
                if (m.upper() == errorName.upper() or almost_equal(m, errorName)):
                    msg += "Did you mean \'" + m + "\' instead of \'" + errorName + "\'? "
                    break

            #Then check if misspelled name
            for m in namesSet:
                if (m.upper() == errorName.upper() or almost_equal(m, errorName)):
                    msg += "Did you mean \'" + m + "\' instead of \'" + errorName + "\'? "
                    break

        self.diagnostics.append(
            {
                "source": "pyflakes",
                "range": err_range,
                "message": msg,
                "severity": severity,
            }
        )
