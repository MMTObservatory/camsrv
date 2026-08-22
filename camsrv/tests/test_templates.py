"""
Static checks on the web templates.

The camera pages drive the cameras entirely from javascript via INDI, so a
reference to an element that doesn't exist in the markup throws a TypeError
part-way through a click handler.  When that happens after the handler has
already called disable(), the controls are never re-enabled and the interface
appears to hang with no indication of what went wrong.
"""

import re

from pathlib import Path

import pytest

TEMPLATE_DIR = Path(__file__).parent.parent / "web_resources" / "templates"
TEMPLATES = sorted(TEMPLATE_DIR.glob("*.html"))

LOOKUP = r"""document\.getElementById\(\s*["']([A-Za-z0-9_-]+)["']\s*\)"""
QUERY = r"""document\.querySelector\(\s*["'][^"']*#([A-Za-z0-9_-]+)["']\s*\)"""


def strip_js_comments(text):
    """
    Remove /* */ blocks and whole-line // comments so that commented-out
    javascript isn't mistaken for live code.  Line comments are only stripped
    when they start a line to avoid mangling URLs such as http://foo.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)
    return text


def strip_dead_functions(text):
    """
    Drop the body of any function whose first statement is an unconditional
    return, since nothing after it can run.
    """
    pattern = re.compile(r"function\s*\w*\s*\([^)]*\)\s*\{\s*return\s*[;\n]")
    while True:
        match = pattern.search(text)
        if match is None:
            return text
        depth = 0
        for i in range(match.start(), len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    text = text[: match.start()] + text[i + 1 :]
                    break
        else:
            return text


def element_ids(text):
    """IDs defined by elements in the markup, ignoring the script blocks."""
    markup = re.sub(r"<script\b.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return set(re.findall(r"""\bid\s*=\s*["']?([A-Za-z0-9_-]+)["']?""", markup))


def guarded_ids(text):
    """
    IDs whose lookup is checked for existence before use, either as a ternary
    (``getElementById('x') ? ... : ...``) or a short circuit
    (``getElementById('x') && ...``).  A guard anywhere counts, since the
    dereference in the taken branch is then safe.
    """
    return set(re.findall(LOOKUP + r"\s*(?:\?|&&)", text)) | set(
        re.findall(QUERY + r"\s*(?:\?|&&)", text)
    )


def dereferenced_ids(text):
    """
    IDs that live javascript looks up and immediately dereferences, e.g.
    ``document.getElementById('expose').disabled``.  These throw if the
    element is missing.
    """
    return set(re.findall(LOOKUP + r"\s*\.", text)) | set(
        re.findall(QUERY + r"\s*\.", text)
    )


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.name)
def test_referenced_elements_exist(template):
    """
    Every element the javascript dereferences without a guard must actually
    exist in the template.
    """
    text = template.read_text()
    live = strip_dead_functions(strip_js_comments(text))
    missing = sorted(dereferenced_ids(live) - guarded_ids(live) - element_ids(text))
    assert not missing, (
        f"{template.name} dereferences element(s) that do not exist in the "
        f"markup: {missing}. Either add the element or guard the lookup."
    )
