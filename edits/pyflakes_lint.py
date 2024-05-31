# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

from pyflakes import api as pyflakes_api
from pyflakes import messages

from pylsp import hookimpl, lsp

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

CUSTOM_VALID_FUNCTIONS = {
    "move",
    "goToXY",
    "goTo",
    "turnRight",
    "turnLeft",
    "pointInDirection",
    "pointTowards",
    "glide",
    "glideTo",
    "ifOnEdgeBounce",
    "setRotationStyle",
    "changeX",
    "setX",
    "changeY",
    "setY",
    "getX",
    "getY",
    "getDirection",
    "say",
    "sayFor",
    "think",
    "thinkFor",
    "show",
    "hide",
    "setCostumeTo",
    "setBackdropTo",
    "setBackdropToAndWait",
    "nextCostume",
    "nextBackdrop",
    "changeGraphicEffectBy",
    "setGraphicEffectTo",
    "clearGraphicEffects",
    "changeSizeBy",
    "setSizeTo",
    "setLayerTo",
    "changeLayerBy",
    "getSize",
    "getCostume",
    "getBackdrop",
    "playSound",
    "playSoundUntilDone",
    "stopAllSounds",
    "setSoundEffectTo",
    "changeSoundEffectBy",
    "clearSoundEffects",
    "setVolumeTo",
    "changeVolumeBy",
    "getVolume",
    "broadcast",
    "broadcastAndWait",
    "isTouching",
    "isTouchingColor",
    "isColorTouchingColor",
    "distanceTo",
    "getTimer",
    "resetTimer",
    "getAttributeOf",
    "getMouseX",
    "getMouseY",
    "isMouseDown",
    "isKeyPressed",
    "current",
    "daysSince2000",
    "getLoudness",
    "getUsername",
    "ask",
    "wait",
    "stop",
    "createClone",
    "deleteClone",
    "erasePen",
    "stampPen",
    "penDown",
    "penUp",
    "setPenColor",
    "changePenEffect",
    "setPenEffect",
    "changePenSize",
    "setPenSize",
    "endThread"
}

@hookimpl
def pylsp_lint(workspace, document):
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

        # Check for custom valid functions
        if isinstance(message, messages.UndefinedName) and message.message_args[0] in CUSTOM_VALID_FUNCTIONS:
            return  # Do not report this as an error or warning

        self.diagnostics.append(
            {
                "source": "pyflakes",
                "range": err_range,
                "message": message.message % message.message_args,
                "severity": severity,
            }
        )
