"""E2E: GFM task-list markdown renders as checkboxes reflecting checked state.

Regression guard for #552. The chat markdown renderer (Streamdown +
remark-gfm) emits a disabled ``<input type=checkbox>`` per ``* [ ]`` /
``* [x]`` item whose ``checked`` attribute mirrors the marker, and
tags the ``<ul>`` with ``contains-task-list`` / the ``<li>`` with
``task-list-item`` so the ``index.css`` overrides can drop the disc
bullet (Streamdown's default ``list-disc`` would otherwise sit a bullet
beside every checkbox) and lay the checkbox beside the text.

A deterministic assistant message is seeded via the
``external_assistant_message`` event (no LLM run) containing one
unchecked task, one checked task, and a plain bullet. The test asserts:

  - two disabled checkboxes render, in the order/states written;
  - the list carries ``contains-task-list`` and the task items carry
    ``task-list-item`` (so the CSS overrides apply);
  - the literal ``[ ]`` / ``[x]`` markers are consumed, not shown;
  - a plain bullet gets no checkbox and no ``task-list-item`` class.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect

_AGENT_NAME = "tasklist_demo"

# One unchecked task, one checked task, then a plain bullet. The plain
# bullet lives in the SAME list as the tasks (remark-gfm tags the <ul>
# ``contains-task-list`` whenever any item is a task) — this proves the
# CSS targets the ``task-list-item`` items only, leaving plain bullets
# with their disc.
_TASK_LIST_TEXT = "Here is my plan:\n\n* [ ] Incomplete\n* [x] Complete\n* plain bullet\n"


@pytest.fixture
def tasklist_session(seeded_session: tuple[str, str]) -> tuple[str, str]:
    """Bind the seeded session and append a task-list assistant bubble.

    Uses ``external_assistant_message`` so the markdown is rendered through
    the real Streamdown pipeline without an LLM turn.

    :param seeded_session: ``(base_url, session_id)`` from the conftest.
    :returns: ``(base_url, session_id)`` with a seeded assistant reply.
    """
    base_url, session_id = seeded_session
    resp = httpx.post(
        f"{base_url}/v1/sessions/{session_id}/events",
        json={
            "type": "external_assistant_message",
            "data": {"agent": _AGENT_NAME, "text": _TASK_LIST_TEXT},
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    return base_url, session_id


def test_chat_renders_task_list_as_checkboxes(
    page: Page,
    tasklist_session: tuple[str, str],
) -> None:
    """`* [ ]`/`* [x]` render as state-reflecting checkboxes; plain bullets don't."""
    base_url, session_id = tasklist_session
    page.goto(f"{base_url}/c/{session_id}")

    # The task-list <ul> is tagged so the index.css overrides apply. Locating
    # on the class (not bare `ul`) avoids matching any prior plain list.
    task_ul = page.locator("ul.contains-task-list").first
    expect(task_ul).to_be_visible(timeout=30_000)

    # Two disabled checkboxes, ordered as written: unchecked then checked.
    checkboxes = task_ul.locator('input[type="checkbox"]')
    expect(checkboxes).to_have_count(2)
    expect(checkboxes.nth(0)).to_have_attribute("disabled", "")
    expect(checkboxes.nth(1)).to_have_attribute("disabled", "")
    expect(checkboxes.nth(0)).not_to_have_attribute("checked", "")
    expect(checkboxes.nth(1)).to_have_attribute("checked", "")

    # The two task items carry `task-list-item` (the CSS hook that drops the
    # disc bullet and lays the checkbox beside the text).
    expect(task_ul.locator("li.task-list-item")).to_have_count(2)

    # The bracket markers must be consumed by the parser, not rendered as text.
    # Scoped to the task <ul> (not <body>) so future UI chrome that happens to
    # render a bracketed string can't flake this assertion.
    expect(task_ul).not_to_contain_text("[ ]")
    expect(task_ul).not_to_contain_text("[x]")

    # The plain bullet sits in the same contains-task-list <ul> but is NOT a
    # task item: no checkbox and no task-list-item class, so it keeps its disc.
    plain_li = task_ul.locator("li:not(.task-list-item)").first
    expect(plain_li).to_contain_text("plain bullet")
    expect(plain_li.locator('input[type="checkbox"]')).to_have_count(0)
