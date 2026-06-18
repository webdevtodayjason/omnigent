"""E2E: the Cursor (cursor-sdk) model switcher sends a valid SDK id, not a
display label.

Regression coverage for #547: the in-chat model switcher for a Cursor
brain-harness session (a bundle agent like Polly with ``harness: "cursor"``)
must send the Cursor SDK model id (e.g. ``composer-2.5``) in the session
override PATCH, not the friendly display label (``Composer``) the picker
shows. The Cursor SDK rejects display labels with an invalid_argument error, so
the picker's ``data-model-id`` (the value written to ``modelOverride``) is the
SDK id while the row text is the display label.

The override PATCH uses the snake_case wire field ``model_override``
(matching ``updateSession`` and the ``collaboration_mode`` convention).

The server fixture seeds a normal ``hello_world`` session; this test patches
the browser's session snapshot into a Cursor brain-harness session (no
``omnigent.wrapper`` label, ``harness: "cursor"``) so the page boots against
the real app/server while the picker is gated on the brain harness.
"""

from __future__ import annotations

import json
from urllib.parse import urlparse

from playwright.sync_api import Page, Route, expect


def _patch_session_as_cursor(page: Page, session_id: str) -> list[dict]:
    """Patch the browser's session snapshot into a Cursor brain-harness session.

    The cursor SDK harness is not a native terminal wrapper, so it carries no
    ``omnigent.wrapper`` label — the model picker is gated on the session's
    ``harness`` field instead. This patches ``GET`` / ``PATCH
    /v1/sessions/{session_id}`` to look like a Polly session running on the
    Cursor brain harness, and echoes back any ``model_override`` written by
    the picker so the optimistic state settles.

    :param page: Playwright page before navigation.
    :param session_id: Session id to patch, e.g. ``"conv_abc123"``.
    :returns: Captured PATCH request bodies.
    """
    latest_payload: dict | None = None
    patch_bodies: list[dict] = []

    def _handle(route: Route) -> None:
        nonlocal latest_payload
        request = route.request
        parsed = urlparse(request.url)
        if parsed.path != f"/v1/sessions/{session_id}":
            route.continue_()
            return

        headers = {"content-type": "application/json"}
        if request.method == "GET":
            response = route.fetch()
            payload = response.json()
            headers = {**response.headers, **headers}
        elif request.method == "PATCH":
            request_body = json.loads(request.post_data or "{}")
            patch_bodies.append(request_body)
            payload = dict(latest_payload or {})
            # updateSession sends snake_case wire fields (``model_override``),
            # not camelCase — same convention as ``collaboration_mode``.
            if "model_override" in request_body:
                payload["model_override"] = request_body["model_override"]
                payload["llm_model"] = request_body["model_override"]
        else:
            route.continue_()
            return

        # Cursor is an SDK brain harness, NOT a native terminal wrapper: it
        # must NOT carry a native wrapper label (the picker is harness-gated).
        labels = dict(payload.get("labels", {}))
        labels.pop("omnigent.wrapper", None)
        payload["labels"] = labels
        payload["harness"] = "cursor"
        payload["llm_model"] = payload.get("llm_model") or "composer-2.5"
        latest_payload = dict(payload)
        route.fulfill(
            status=200,
            headers=headers,
            body=json.dumps(payload),
        )

    page.route("**/v1/sessions/**", _handle)
    return patch_bodies


def test_cursor_picker_sends_sdk_id_not_display_label(
    page: Page,
    seeded_session: tuple[str, str],
) -> None:
    """Selecting ``Composer`` writes ``composer-2.5`` to the model override.

    The picker row shows the display label ``Composer`` but carries the Cursor
    SDK id ``composer-2.5`` as its ``data-model-id`` — the value the store
    writes to ``model_override``. Sending the display label would trip the
    SDK's ``Cannot use this model: Composer`` rejection (#547).

    :param page: Playwright page fixture.
    :param seeded_session: ``(base_url, session_id)`` for a real server-backed
        session; the browser snapshot is patched to a Cursor brain harness.
    :returns: None.
    """
    base_url, session_id = seeded_session
    patch_bodies = _patch_session_as_cursor(page, session_id)

    page.goto(f"{base_url}/c/{session_id}")

    trigger = page.get_by_test_id("agent-picker-trigger")
    expect(trigger).to_be_visible(timeout=15_000)
    # The Cursor brain harness reads as the identity suffix — "Polly (Cursor)".
    expect(trigger).to_contain_text("Cursor")
    trigger.click()

    # The Composer row shows the display label but carries the SDK id.
    composer_row = page.locator('[data-testid="model-picker-item"][data-model-id="composer-2.5"]')
    expect(composer_row).to_be_visible()
    expect(composer_row).to_contain_text("Composer")
    # The display label must never leak as the model id the picker sends.
    assert page.locator('[data-testid="model-picker-item"][data-model-id="Composer"]').count() == 0

    with page.expect_response(
        lambda response: (
            response.request.method == "PATCH"
            and urlparse(response.url).path == f"/v1/sessions/{session_id}"
            and response.status == 200
        )
    ):
        composer_row.click()

    # The core #547 fix: the override PATCH carries the SDK id, not the display
    # label the user clicked.
    assert patch_bodies[-1] == {"model_override": "composer-2.5"}
