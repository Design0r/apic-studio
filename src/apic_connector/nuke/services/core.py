from __future__ import absolute_import

import os

import nuke

from ..compat import Logger

# file knobs that hold plugin icon names, not paths relative to the project
_SKIP_FILE_KNOBS = ("icon",)


def open_file(file_path):
    if not os.path.isfile(file_path):
        Logger.error("open file failed, file does not exist: {}".format(file_path))
        return False

    # opens in this session if the current script is empty, otherwise nuke
    # starts a new instance, so unsaved changes are never discarded
    try:
        nuke.scriptOpen(file_path)
    except RuntimeError as e:
        Logger.error("open file failed: {}: {}".format(file_path, e))
        return False

    Logger.info("open file succeeded: {}".format(file_path))
    return True


def _same_path(a, b):
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(
        os.path.normpath(b)
    )


def open_file_in_place(file_path):
    """
    Opens the file in this session. The current script is cleared first, which
    keeps nuke from starting a new instance but discards unsaved changes.
    """
    if not os.path.isfile(file_path):
        Logger.error("open file failed, file does not exist: {}".format(file_path))
        return False

    root = nuke.root()
    if root.modified():
        Logger.warning("discarding unsaved changes of {}".format(root.name()))

    try:
        nuke.scriptClear()
        nuke.scriptOpen(file_path)
    except RuntimeError as e:
        Logger.error("open file failed: {}: {}".format(file_path, e))
        return False

    # scriptOpen falls back to a new instance if it doesn't consider the
    # cleared script empty, catch that instead of reporting success
    if not _same_path(nuke.root().name(), file_path):
        Logger.error("open file in place failed, opened in a new instance")
        return False

    Logger.info("open file in place succeeded: {}".format(file_path))
    return True


def import_file(file_path):
    if not os.path.isfile(file_path):
        Logger.error("import failed, file does not exist: {}".format(file_path))
        return False

    # same as File > Import Script, pastes the script's nodes into the open one
    try:
        nuke.nodePaste(file_path)
    except RuntimeError as e:
        Logger.error("import failed: {}: {}".format(file_path, e))
        return False

    Logger.info("import succeeded: {}".format(file_path))
    return True


def _project_directory():
    project_dir = nuke.root()["project_directory"].evaluate()
    return project_dir or os.getcwd()


def _relative_file_knobs():
    for node in nuke.allNodes(recurseGroups=True):
        for knob in node.allKnobs():
            if knob.Class() != "File_Knob" or knob.name() in _SKIP_FILE_KNOBS:
                continue

            value = knob.getValue()
            # skip empty, absolute and tcl / env var driven paths
            if not value or "[" in value or value.startswith("$"):
                continue
            if os.path.isabs(value):
                continue

            yield knob, value


def save_file_as(file_path, globalize_textures):
    """
    Saves a copy of the current script. The open script keeps its name and
    modified state, unlike nuke.scriptSave(path) which marks it as saved.
    """
    root = nuke.root()
    was_modified = root.modified()
    globalized = []

    if globalize_textures:
        project_dir = _project_directory()
        for knob, value in _relative_file_knobs():
            absolute = os.path.normpath(os.path.join(project_dir, value))
            knob.setValue(absolute.replace("\\", "/"))
            globalized.append((knob, value))

    try:
        nuke.scriptSaveToTemp(file_path)
    except RuntimeError as e:
        Logger.error("save scene failed: {}: {}".format(file_path, e))
        return False
    finally:
        # globalizing only applies to the saved copy
        for knob, value in globalized:
            knob.setValue(value)
        root.setModified(was_modified)

    Logger.info("save scene succeeded: {}".format(file_path))
    return True
