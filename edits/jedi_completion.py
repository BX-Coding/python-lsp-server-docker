# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import logging
import os

import parso

from pylsp import _utils, hookimpl, lsp
from pylsp.plugins._resolvers import LABEL_RESOLVER, SNIPPET_RESOLVER

log = logging.getLogger(__name__)

# Map to the LSP type
# > Valid values for type are ``module``, `` class ``, ``instance``, ``function``,
# > ``param``, ``path``, ``keyword``, ``property`` and ``statement``.
# see: https://jedi.readthedocs.io/en/latest/docs/api-classes.html#jedi.api.classes.BaseName.type
_TYPE_MAP = {
    "module": lsp.CompletionItemKind.Module,
    "namespace": lsp.CompletionItemKind.Module,  # to be added in Jedi 0.18+
    "class": lsp.CompletionItemKind.Class,
    "instance": lsp.CompletionItemKind.Reference,
    "function": lsp.CompletionItemKind.Function,
    "param": lsp.CompletionItemKind.Variable,
    "path": lsp.CompletionItemKind.File,
    "keyword": lsp.CompletionItemKind.Keyword,
    "property": lsp.CompletionItemKind.Property,  # added in Jedi 0.18
    "statement": lsp.CompletionItemKind.Variable,
}

# Types of parso nodes for which snippet is not included in the completion
_IMPORTS = ("import_name", "import_from")

# Types of parso node for errors
_ERRORS = ("error_node",)

patchApi = [
    {
        "name": "move",
        "opcode": "motion_movesteps",
        "parameters": ["steps"],
        "exampleParameters": {"steps": 10},
    },
    {
        "name": "goToXY",
        "opcode": "motion_gotoxy",
        "parameters": ["x", "y"],
        "exampleParameters": {"x": "PrimProxy.DEFAULT_X", "y": "PrimProxy.DEFAULT_Y"},
    },
    {
        "name": "goTo",
        "opcode": "motion_goto",
        "parameters": ["name"],
        "exampleParameters": {"name": "PrimProxy.LOCATION_OPTIONS"},
    },
    {
        "name": "turnRight",
        "opcode": "motion_turnright",
        "parameters": ["degrees"],
        "exampleParameters": {"degrees": "PrimProxy.DEFAULT_DIRECTION"},
    },
    {
        "name": "turnLeft",
        "opcode": "motion_turnleft",
        "parameters": ["degrees"],
        "exampleParameters": {"degrees": "PrimProxy.DEFAULT_DIRECTION"},
    },
    {
        "name": "pointInDirection",
        "opcode": "motion_pointindirection",
        "parameters": ["degrees"],
        "exampleParameters": {"degrees": "PrimProxy.DEFAULT_DIRECTION"},
    },
    {
        "name": "pointTowards",
        "opcode": "motion_pointtowards",
        "parameters": ["name"],
        "exampleParameters": {"name": "PrimProxy.LOCATION_OPTIONS"},
    },
    {
        "name": "glide",
        "opcode": "motion_glidesecstoxy",
        "parameters": ["seconds", "x", "y"],
        "exampleParameters": {
            "seconds": "PrimProxy.DEFAULT_SECONDS",
            "x": "PrimProxy.DEFAULT_X",
            "y": "PrimProxy.DEFAULT_Y",
        },
    },
    {
        "name": "glideTo",
        "opcode": "motion_glideto",
        "parameters": ["seconds", "name"],
        "exampleParameters": {
            "seconds": "PrimProxy.DEFAULT_SECONDS",
            "name": "PrimProxy.LOCATION_OPTIONS",
        },
    },
    {
        "name": "ifOnEdgeBounce",
        "opcode": "motion_ifonedgebounce",
        "parameters": [],
        "exampleParameters": {},
    },
    {
        "name": "setRotationStyle",
        "opcode": "motion_setrotationstyle",
        "parameters": ["style"],
        "exampleParameters": {"style": "Scratch3MotionBlocks.ROTATION_STYLES"},
    },
    {
        "name": "changeX",
        "opcode": "motion_changexby",
        "parameters": ["x"],
        "exampleParameters": {"x": "PrimProxy.DEFAULT_CHANGE"},
    },
    {
        "name": "setX",
        "opcode": "motion_setx",
        "parameters": ["x"],
        "exampleParameters": {"x": "PrimProxy.DEFAULT_X"},
    },
    {
        "name": "changeY",
        "opcode": "motion_changeyby",
        "parameters": ["y"],
        "exampleParameters": {"y": "PrimProxy.DEFAULT_CHANGE"},
    },
    {
        "name": "setY",
        "opcode": "motion_sety",
        "parameters": ["y"],
        "exampleParameters": {"y": "PrimProxy.DEFAULT_Y"},
    },
    {
        "name": "getX",
        "opcode": "motion_xposition",
        "parameters": [],
        "exampleParameters": {},
    },
    {
        "name": "getY",
        "opcode": "motion_yposition",
        "parameters": [],
        "exampleParameters": {},
    },
    {
        "name": "getDirection",
        "opcode": "motion_direction",
        "parameters": [],
        "exampleParameters": {},
    },
    {
        "name": "say",
        "opcode": "looks_say",
        "parameters": ["message"],
        "exampleParameters": {"message": "PrimProxy.DEFAULT_MESSAGE"},
    },
    {
        "name": "sayFor",
        "opcode": "looks_sayforsecs",
        "parameters": ["message", "secs"],
        "exampleParameters": {"message": "PrimProxy.DEFAULT_MESSAGE"},
    },
    {
        "name": "think",
        "opcode": "looks_think",
        "parameters": ["message"],
        "exampleParameters": {"message": "PrimProxy.DEFAULT_MESSAGE"},
    },
    {
        "name": "thinkFor",
        "opcode": "looks_thinkforsecs",
        "parameters": ["message", "secs"],
        "exampleParameters": {"message": "PrimProxy.DEFAULT_MESSAGE"},
    },
    {
        "name": "show",
        "opcode": "looks_show",
        "parameters": [],
        "exampleParameters": {},
    },
    {
        "name": "hide",
        "opcode": "looks_hide",
        "parameters": [],
        "exampleParameters": {},
    },
    {
        "name": "setCostumeTo",
        "opcode": "looks_switchcostumeto",
        "parameters": ["name"],
        "exampleParameters": {"name": "PrimProxy.COSTUME_NAMES"},
    },
    {
        "name": "setBackdropTo",
        "opcode": "looks_switchbackdropto",
        "parameters": ["name"],
        "exampleParameters": {"name": "PrimProxy.BACKDROP_NAMES"},
    },
    {
        "name": "setBackdropToAndWait",
        "opcode": "looks_switchbackdroptoandwait",
        "parameters": ["name"],
        "exampleParameters": {"name": "PrimProxy.BACKDROP_NAMES"},
    },
    {
        "name": "nextCostume",
        "opcode": "looks_nextcostume",
        "parameters": [],
        "exampleParameters": {},
    },
    {
        "name": "nextBackdrop",
        "opcode": "looks_nextbackdrop",
        "parameters": [],
        "exampleParameters": {},
    },
    {
        "name": "changeGraphicEffectBy",
        "opcode": "looks_changeeffectby",
        "parameters": ["effect", "change"],
        "exampleParameters": {
            "effect": "Scratch3LooksBlocks.EFFECT_LIST",
            "change": "PrimProxy.DEFAULT_CHANGE",
        },
    },
    {
        "name": "setGraphicEffectTo",
        "opcode": "looks_seteffectto",
        "parameters": ["effect", "value"],
        "exampleParameters": {
            "effect": "Scratch3LooksBlocks.EFFECT_LIST",
            "value": "PrimProxy.DEFAULT_EFFECT",
        },
    },
    {
        "name": "clearGraphicEffects",
        "opcode": "looks_cleargraphiceffects",
        "parameters": [],
        "exampleParameters": {},
    },
    {
        "name": "changeSizeBy",
        "opcode": "looks_changesizeby",
        "parameters": ["change"],
        "exampleParameters": {"change": "PrimProxy.DEFAULT_CHANGE"},
    },
    {
        "name": "setSizeTo",
        "opcode": "looks_setsizeto",
        "parameters": ["size"],
        "exampleParameters": {"size": "PrimProxy.DEFAULT_SIZE"},
    },
    {
        "name": "setLayerTo",
        "opcode": "looks_gotofrontback",
        "parameters": ["layer"],
        "exampleParameters": {"layer": ["front", "back"]}
    },
    {
        "name": "changeLayerBy",
        "opcode": "looks_goforwardbackwardlayers",
        "parameters": ["direction", "change"],
        "exampleParameters": {"direction": "forward", "change": 1}
    },
    {
        "name": "getSize",
        "opcode": "looks_size",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "getCostume",
        "opcode": "looks_costumenumbername",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "getBackdrop",
        "opcode": "looks_backdropnumbername",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "playSound",
        "opcode": "sound_play",
        "parameters": ["soundName"],
        "exampleParameters": {"soundName": "PrimProxy.SOUND_NAMES"}
    },
    {
        "name": "playSoundUntilDone",
        "opcode": "sound_playuntildone",
        "parameters": ["sound name"],
        "exampleParameters": {"soundName": "PrimProxy.SOUND_NAMES"}
    },
    {
        "name": "stopAllSounds",
        "opcode": "sound_stopallsounds",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "setSoundEffectTo",
        "opcode": "sound_seteffectto",
        "parameters": ["effect", "value"],
        "exampleParameters": {"effect": "Scratch3SoundBlocks.EFFECT_LIST", "value": "PrimProxy.DEFAULT_EFFECT"}
    },
    {
        "name": "changeSoundEffectBy",
        "opcode": "sound_changeeffectby",
        "parameters": ["effect", "change"],
        "exampleParameters": {"effect": "Scratch3SoundBlocks.EFFECT_LIST", "change": "PrimProxy.DEFAULT_CHANGE"}
    },
    {
        "name": "clearSoundEffects",
        "opcode": "sound_cleareffects",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "setVolumeTo",
        "opcode": "sound_setvolumeto",
        "parameters": ["volume"],
        "exampleParameters": {"volume": "PrimProxy.DEFAULT_VOLUME"}
    },
    {
        "name": "changeVolumeBy",
        "opcode": "sound_changevolumeby",
        "parameters": ["change"],
        "exampleParameters": {"change": "PrimProxy.DEFAULT_CHANGE"}
    },
    {
        "name": "getVolume",
        "opcode": "sound_volume",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "broadcast",
        "opcode": "event_broadcast",
        "parameters": ["message"],
        "exampleParameters": {"message": "PrimProxy.MESSAGE_NAMES"}
    },
    {
        "name": "broadcastAndWait",
        "opcode": "event_broadcastandwait",
        "parameters": ["message"],
        "exampleParameters": {"message": "PrimProxy.MESSAGE_NAMES"}
    },
    {
        "name": "isTouching",
        "opcode": "sensing_touchingobject",
        "parameters": ["name"],
        "exampleParameters": {"name": "PrimProxy.TOUCHING_OPTIONS"}
    },
    {
        "name": "isTouchingColor",
        "opcode": "sensing_touchingcolor",
        "parameters": ["color"],
        "exampleParameters": {"color": "PrimProxy.DEFAULT_EFFECT"}
    },
    {
        "name": "isColorTouchingColor",
        "opcode": "sensing_coloristouchingcolor",
        "parameters": ["color1", "color2"],
        "exampleParameters": {"color1": "PrimProxy.DEFAULT_EFFECT", "color2": "PrimProxy.DEFAULT_EFFECT"}
    },
    {
        "name": "distanceTo",
        "opcode": "sensing_distanceto",
        "parameters": ["name"],
        "exampleParameters": {"name": "PrimProxy.LOCATION_OPTIONS"}
    },
    {
        "name": "getTimer",
        "opcode": "sensing_timer",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "resetTimer",
        "opcode": "sensing_resettimer",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "getAttributeOf",
        "opcode": "sensing_of",
        "parameters": ["object", "property"],
        "exampleParameters": {"object": "PrimProxy.TARGET_NAMES", "property": "x position"}
    },
    {
        "name": "getMouseX",
        "opcode": "sensing_mousex",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "getMouseY",
        "opcode": "sensing_mousey",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "isMouseDown",
        "opcode": "sensing_mousedown",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "isKeyPressed",
        "opcode": "sensing_keypressed",
        "parameters": ["key"],
        "exampleParameters": {"key": "PrimProxy.KEY_DOWN_OPTIONS"}
    },
    {
        "name": "current",
        "opcode": "sensing_current",
        "parameters": ["timeIncrement"],
        "exampleParameters": {"timeIncrement": "Scratch3SensingBlocks.CURRENT_INCREMENT_OPTIONS"}
    },
    {
        "name": "daysSince2000",
        "opcode": "sensing_dayssince2000",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "getLoudness",
        "opcode": "sensing_loudness",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "getUsername",
        "opcode": "sensing_username",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "ask",
        "opcode": "sensing_askandwait",
        "parameters": ["question"],
        "exampleParameters": {"question": "PrimProxy.DEFAULT_QUESTION"}
    },
    {
        "name": "wait",
        "opcode": "control_wait",
        "parameters": ["seconds"],
        "exampleParameters": {"seconds": "PrimProxy.DEFAULT_SECONDS"}
    },
    {
        "name": "stop",
        "opcode": "control_stop",
        "parameters": ["option"],
        "exampleParameters": {"option": "Scratch3ControlBlocks.STOP_OPTIONS"}
    },
    {
        "name": "createClone",
        "opcode": "control_create_clone_of",
        "parameters": ["option"],
        "exampleParameters": {"option": "PrimProxy.CLONE_OPTIONS"}
    },
    {
        "name": "deleteClone",
        "opcode": "control_delete_this_clone",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "erasePen",
        "opcode": "pen_clear",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "stampPen",
        "opcode": "pen_stamp",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "penDown",
        "opcode": "pen_pendown",
        "parameters": [],
    },
    {
        "name": "penUp",
        "opcode": "pen_penup",
        "parameters": [],
        "exampleParameters": {}
    },
    {
        "name": "setPenColor",
        "opcode": "pen_setpencolortocolor",
        "parameters": ["color"],
        "exampleParameters": {"color": "PrimProxy.DEFAULT_EFFECT"}
    },
    {
        "name": "changePenEffect",
        "opcode": "pen_changepencolorparamby",
        "parameters": ["effect", "change"],
        "exampleParameters": {"effect": "Scratch3PenBlocks.PEN_EFFECT_LIST", "change": "PrimProxy.DEFAULT_CHANGE"}
    },
    {
        "name": "setPenEffect",
        "opcode": "pen_setpencolorparamto",
        "parameters": ["effect", "value"],
        "exampleParameters": {"effect": "Scratch3PenBlocks.PEN_EFFECT_LIST", "value": "PrimProxy.DEFAULT_EFFECT"}
    },
    {
        "name": "changePenSize",
        "opcode": "pen_changepensizeby",
        "parameters": ["change"],
        "exampleParameters": {"change": "PrimProxy.DEFAULT_CHANGE"}
    },
    {
        "name": "setPenSize",
        "opcode": "pen_setpensizeto",
        "parameters": ["size"],
        "exampleParameters": {"size": "PrimProxy.DEFAULT_SIZE"}
    },
    {
        "name": "endThread",
        "opcode": "core_endthread",
        "parameters": [],
        "exampleParameters": {}
    }
]

class CustomCompletion:
    def __init__(self, name, type):
        self.full_name = ""
        self.name = name
        self.type = type
        self._docstring = ""
        self._signatures = []

    def docstring(self):
        return self._docstring

    def get_signatures(self):
        return self._signatures

def addPatchCompletes(list):
    """Returns a list of custom completion items"""
    for f in patchApi:
        name = f["name"]
        parameters = f["parameters"]
        funcName = f"{name}({', '.join(parameters)})"

        list.append(CustomCompletion(name=funcName, type="function", ))
    
@hookimpl
def pylsp_completions(config, document, position):
    """Get formatted completions for current code position"""
    settings = config.plugin_settings("jedi_completion", document_path=document.path)
    resolve_eagerly = settings.get("eager", False)
    code_position = _utils.position_to_jedi_linecolumn(document, position)

    code_position["fuzzy"] = settings.get("fuzzy", False)

    completions = document.jedi_script(use_document_path=True).complete(**code_position)
    addPatchCompletes(completions)
    
    if not completions:
        return None

    completion_capabilities = config.capabilities.get("textDocument", {}).get(
        "completion", {}
    )
    item_capabilities = completion_capabilities.get("completionItem", {})
    snippet_support = item_capabilities.get("snippetSupport")
    supported_markup_kinds = item_capabilities.get("documentationFormat", ["markdown"])
    preferred_markup_kind = _utils.choose_markup_kind(supported_markup_kinds)

    should_include_params = settings.get("include_params")
    should_include_class_objects = settings.get("include_class_objects", False)
    should_include_function_objects = settings.get("include_function_objects", False)

    max_to_resolve = settings.get("resolve_at_most", 25)
    modules_to_cache_for = settings.get("cache_for", None)
    if modules_to_cache_for is not None:
        LABEL_RESOLVER.cached_modules = modules_to_cache_for
        SNIPPET_RESOLVER.cached_modules = modules_to_cache_for

    include_params = (
        snippet_support and should_include_params and use_snippets(document, position)
    )
    include_class_objects = (
        snippet_support
        and should_include_class_objects
        and use_snippets(document, position)
    )
    include_function_objects = (
        snippet_support
        and should_include_function_objects
        and use_snippets(document, position)
    )

    ready_completions = [
        _format_completion(
            c,
            markup_kind=preferred_markup_kind,
            include_params=include_params if c.type in ["class", "function"] else False,
            resolve=resolve_eagerly,
            resolve_label_or_snippet=(i < max_to_resolve),
            snippet_support=snippet_support,
        )
        for i, c in enumerate(completions)
    ]

    # TODO split up once other improvements are merged
    if include_class_objects:
        for i, c in enumerate(completions):
            if c.type == "class":
                completion_dict = _format_completion(
                    c,
                    markup_kind=preferred_markup_kind,
                    include_params=False,
                    resolve=resolve_eagerly,
                    resolve_label_or_snippet=(i < max_to_resolve),
                    snippet_support=snippet_support,
                )
                completion_dict["kind"] = lsp.CompletionItemKind.TypeParameter
                completion_dict["label"] += " object"
                ready_completions.append(completion_dict)

    if include_function_objects:
        for i, c in enumerate(completions):
            if c.type == "function":
                completion_dict = _format_completion(
                    c,
                    markup_kind=preferred_markup_kind,
                    include_params=False,
                    resolve=resolve_eagerly,
                    resolve_label_or_snippet=(i < max_to_resolve),
                    snippet_support=snippet_support,
                )
                completion_dict["kind"] = lsp.CompletionItemKind.TypeParameter
                completion_dict["label"] += " object"
                ready_completions.append(completion_dict)

    for completion_dict in ready_completions:
        completion_dict["data"] = {"doc_uri": document.uri}

    # Add custom completions
   

    # most recently retrieved completion items, used for resolution
    document.shared_data["LAST_JEDI_COMPLETIONS"] = {
        # label is the only required property; here it is assumed to be unique
        completion["label"]: (completion, data)
        for completion, data in zip(ready_completions, completions)
    }

    # print(ready_completions)
    return ready_completions or None


@hookimpl
def pylsp_completion_item_resolve(config, completion_item, document):
    """Resolve formatted completion for given non-resolved completion"""
    shared_data = document.shared_data["LAST_JEDI_COMPLETIONS"].get(
        completion_item["label"]
    )

    completion_capabilities = config.capabilities.get("textDocument", {}).get(
        "completion", {}
    )
    item_capabilities = completion_capabilities.get("completionItem", {})
    supported_markup_kinds = item_capabilities.get("documentationFormat", ["markdown"])
    preferred_markup_kind = _utils.choose_markup_kind(supported_markup_kinds)

    if shared_data:
        completion, data = shared_data
        return _resolve_completion(completion, data, markup_kind=preferred_markup_kind)
    return completion_item


def is_exception_class(name):
    """
    Determine if a class name is an instance of an Exception.

    This returns `False` if the name given corresponds with a instance of
    the 'Exception' class, `True` otherwise
    """
    try:
        return name in [cls.__name__ for cls in Exception.__subclasses__()]
    except AttributeError:
        # Needed in case a class don't uses new-style
        # class definition in Python 2
        return False


def use_snippets(document, position):
    """
    Determine if it's necessary to return snippets in code completions.

    This returns `False` if a completion is being requested on an import
    statement, `True` otherwise.
    """
    line = position["line"]
    lines = document.source.split("\n", line)
    act_lines = [lines[line][: position["character"]]]
    line -= 1
    last_character = ""
    while line > -1:
        act_line = lines[line]
        if (
            act_line.rstrip().endswith("\\")
            or act_line.rstrip().endswith("(")
            or act_line.rstrip().endswith(",")
        ):
            act_lines.insert(0, act_line)
            line -= 1
            if act_line.rstrip().endswith("("):
                # Needs to be added to the end of the code before parsing
                # to make it valid, otherwise the node type could end
                # being an 'error_node' for multi-line imports that use '('
                last_character = ")"
        else:
            break
    if "(" in act_lines[-1].strip():
        last_character = ")"
    code = "\n".join(act_lines).rsplit(";", maxsplit=1)[-1].strip() + last_character
    tokens = parso.parse(code)
    expr_type = tokens.children[0].type
    return expr_type not in _IMPORTS and not (expr_type in _ERRORS and "import" in code)


def _resolve_completion(completion, d, markup_kind: str):
    completion["detail"] = _detail(d)
    try:
        docs = _utils.format_docstring(
            d.docstring(raw=True),
            signatures=[signature.to_string() for signature in d.get_signatures()],
            markup_kind=markup_kind,
        )
    except Exception:
        docs = ""
    completion["documentation"] = docs
    return completion


def _format_completion(
    d,
    markup_kind: str,
    include_params=True,
    resolve=False,
    resolve_label_or_snippet=False,
    snippet_support=False,
):
    completion = {
        "label": _label(d, resolve_label_or_snippet),
        "kind": _TYPE_MAP.get(d.type),
        "sortText": _sort_text(d),
        "insertText": d.name,
    }

    if resolve:
        completion = _resolve_completion(completion, d, markup_kind)

    # Adjustments for file completions
    if d.type == "path":
        path = os.path.normpath(d.name)

        # If the completion ends with os.sep, it means it's a directory. So we add os.sep at the end
        # to ease additional file completions.
        if d.name.endswith(os.sep):
            if os.name == "nt":
                path = path + "\\"
            else:
                path = path + "/"

        # Escape to prevent conflicts with the code snippets grammer
        # See also https://github.com/python-lsp/python-lsp-server/issues/373
        if snippet_support:
            path = path.replace("\\", "\\\\")
            path = path.replace("/", "\\/")

        completion["insertText"] = path

    if include_params and not is_exception_class(d.name):
        snippet = _snippet(d, resolve_label_or_snippet)
        completion.update(snippet)

    return completion


def _label(definition, resolve=False):
    if not resolve:
        return definition.name
    sig = LABEL_RESOLVER.get_or_create(definition)
    if sig:
        return sig
    return definition.name


def _snippet(definition, resolve=False):
    if not resolve:
        return {}
    snippet = SNIPPET_RESOLVER.get_or_create(definition)
    return snippet


def _detail(definition):
    try:
        return definition.parent().full_name or ""
    except AttributeError:
        return definition.full_name or ""


def _sort_text(definition):
    """Ensure builtins appear at the bottom.
    Description is of format <type>: <module>.<item>
    """

    # If its 'hidden', put it next last
    prefix = "z{}" if definition.name.startswith("_") else "a{}"
    return prefix.format(definition.name)
