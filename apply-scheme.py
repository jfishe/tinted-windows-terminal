#!/usr/bin/env python3
"""Upsert the "Tinty" color scheme into Windows Terminal's settings.json.

Usage: apply-scheme.py SCHEME_JSON [SETTINGS_JSON]

settings.json is JSONC (comments, trailing commas), so it is edited as text:
only the span of the existing "Tinty" object in "schemes" is replaced (or the
object is inserted as the first element), leaving comments and formatting
elsewhere untouched.
"""

import json
import os
import re
import shutil
import sys
import tempfile

DEFAULT_SETTINGS = os.path.expanduser(
    "~/userprofile/AppData/Local/Packages/"
    "Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState/settings.json"
)
NAME = "Tinty"


CODE, STRING, COMMENT = 0, 1, 2


def classify(text):
    """Per-character kind: CODE, STRING (contents between quotes) or COMMENT."""
    kinds = [CODE] * len(text)
    i, n = 0, len(text)
    while i < n:
        if text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            lo, hi, kind, end = i + 1, j, STRING, j + 1
        elif text.startswith("//", i):
            end = text.find("\n", i)
            end = n if end < 0 else end
            lo, hi, kind = i, end, COMMENT
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            lo, hi, kind = i, end, COMMENT
        else:
            i += 1
            continue
        kinds[lo:hi] = [kind] * (hi - lo)
        i = end
    return kinds


def code_mask(text):
    return [k == CODE for k in classify(text)]


def loads_jsonc(text):
    """json.loads after blanking comments and dropping trailing commas."""
    kinds = classify(text)
    out = [" " if k == COMMENT else c for c, k in zip(text, kinds)]
    mask = [k == CODE for k in kinds]
    for i, c in enumerate(out):
        if c == "," and mask[i]:
            j = next_code(out, mask, i + 1)
            if j < len(out) and out[j] in "}]":
                out[i] = " "
    return json.loads("".join(out))


def match(text, mask, start):
    """Index just past the bracket matching text[start]."""
    depth = 0
    for i in range(start, len(text)):
        if not mask[i]:
            continue
        if text[i] in "[{":
            depth += 1
        elif text[i] in "]}":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError(f"unbalanced bracket at offset {start}")


def next_code(text, mask, i):
    while i < len(text) and (not mask[i] or text[i].isspace()):
        i += 1
    return i


def find_schemes(text, mask):
    """Offset of the '[' of the top-level "schemes" array."""
    top = next_code(text, mask, 0)
    if text[top : top + 1] != "{":
        raise ValueError("settings.json is not an object")
    for m in re.finditer(r'"schemes"', text):
        i = m.start()
        if not mask[i]:
            continue
        depth = sum(
            1 if text[k] in "[{" else -1
            for k in range(top, i)
            if mask[k] and text[k] in "[]{}"
        )
        if depth != 1:
            continue
        j = next_code(text, mask, m.end())
        if text[j : j + 1] != ":":
            continue
        j = next_code(text, mask, j + 1)
        if text[j : j + 1] == "[":
            return j
    raise ValueError('top-level "schemes" array not found')


def elements(text, mask, lbracket):
    """(start, end) spans of the object elements of the array."""
    rbracket = match(text, mask, lbracket) - 1
    spans, i = [], lbracket + 1
    while True:
        i = next_code(text, mask, i)
        if i >= rbracket:
            return spans, rbracket
        if text[i] == "{":
            end = match(text, mask, i)
            spans.append((i, end))
            i = end
        else:
            i += 1


def line_indent(text, i):
    bol = text.rfind("\n", 0, i) + 1
    return re.match(r"[ \t]*", text[bol:]).group()


def render(scheme, indent):
    body = json.dumps(scheme, indent=4, ensure_ascii=False)
    return body.replace("\n", "\n" + indent)


def upsert(text, scheme):
    mask = code_mask(text)
    lbracket = find_schemes(text, mask)
    spans, rbracket = elements(text, mask, lbracket)
    for start, end in spans:
        if loads_jsonc(text[start:end]).get("name") == NAME:
            new = render(scheme, line_indent(text, start))
            return text[:start] + new + text[end:]
    if spans:
        indent = line_indent(text, spans[0][0])
        new = render(scheme, indent)
        return text[: spans[0][0]] + new + ",\n" + indent + text[spans[0][0] :]
    outer = line_indent(text, lbracket)
    indent = outer + "    "
    new = render(scheme, indent)
    inner = "\n" + indent + new + "\n" + outer
    return text[: lbracket + 1] + inner + text[rbracket:]


def main(argv):
    if len(argv) not in (2, 3):
        sys.exit(__doc__)
    scheme_path = argv[1]
    settings_path = argv[2] if len(argv) == 3 else DEFAULT_SETTINGS

    with open(scheme_path, encoding="utf-8") as f:
        scheme = json.load(f)
    scheme["name"] = NAME
    with open(settings_path, encoding="utf-8-sig") as f:
        text = f.read()

    try:
        new = upsert(text, scheme)
        schemes = loads_jsonc(new)["schemes"]
    except ValueError as e:
        sys.exit(f"apply-scheme: {settings_path}: {e}")
    if sum(s.get("name") == NAME for s in schemes) != 1:
        sys.exit(f"apply-scheme: expected exactly one {NAME!r} scheme")
    if new == text:
        return

    shutil.copy2(settings_path, settings_path + ".tinty.bak")
    d = os.path.dirname(os.path.abspath(settings_path))
    fd, tmp = tempfile.mkstemp(prefix=".settings.", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(new)
        shutil.copymode(settings_path, tmp)
        os.replace(tmp, settings_path)
    except BaseException:
        os.unlink(tmp)
        raise


if __name__ == "__main__":
    main(sys.argv)
