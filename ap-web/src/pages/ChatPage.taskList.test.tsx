import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { Bubble } from "@/lib/renderItems";
import { FileViewerContext } from "@/shell/FileViewerContext";
import { BubbleView } from "./ChatPage";

// Task-list markdown (`* [ ]` / `* [x]`) flows through the same Streamdown
// renderer as the rest of the chat (FilePathAwareMessageResponse). These
// tests pin the GFM task-list wiring that #552 fixed: remark-gfm emits a
// disabled <input type=checkbox> per item whose `checked` mirrors the marker,
// and tags the <ul> with `contains-task-list` / <li> with `task-list-item` so
// the index.css overrides can drop the disc bullet and lay the checkbox
// beside the text. If the wiring regresses (e.g. remark-gfm dropped from the
// default remark plugins), the checkboxes vanish and these assertions fail.

afterEach(cleanup);

const FILE_VIEWER_NOOP = {
  openFile: () => {},
  isChangedPath: () => false,
  conversationId: undefined,
  workspaceRoot: null,
  workspaceHome: null,
};

function assistantBubble(text: string): Extract<Bubble, { kind: "assistant" }> {
  return {
    kind: "assistant",
    responseId: "codex_turn_123",
    stableId: "msg_1",
    lifecycle: "completed",
    error: null,
    items: [{ kind: "text", itemId: "msg_1", text, final: true }],
  };
}

function userBubble(text: string): Extract<Bubble, { kind: "user" }> {
  return {
    kind: "user" as const,
    itemId: "u1",
    content: [{ type: "input_text" as const, text }],
  };
}

function renderBubble(bubble: Bubble) {
  return render(
    <FileViewerContext.Provider value={FILE_VIEWER_NOOP}>
      <BubbleView bubble={bubble} />
    </FileViewerContext.Provider>,
  );
}

describe("Task-list markdown rendering", () => {
  it("renders `* [ ]` / `* [x]` items as disabled checkboxes reflecting state", () => {
    const { container } = renderBubble(assistantBubble("* [ ] Incomplete\n* [x] Complete"));

    const checkboxes = container.querySelectorAll('input[type="checkbox"]');
    expect(checkboxes).toHaveLength(2);
    // Both checkboxes are disabled (read-only render of agent output).
    expect(checkboxes[0]!.hasAttribute("disabled")).toBe(true);
    expect(checkboxes[1]!.hasAttribute("disabled")).toBe(true);
    // State mirrors the marker: `[ ]` -> unchecked, `[x]` -> checked.
    expect(checkboxes[0]!.hasAttribute("checked")).toBe(false);
    expect(checkboxes[1]!.hasAttribute("checked")).toBe(true);
  });

  it("tags the list so the CSS overrides apply (contains-task-list / task-list-item)", () => {
    const { container } = renderBubble(assistantBubble("* [ ] Incomplete\n* [x] Complete"));

    const ul = container.querySelector("ul");
    expect(ul).not.toBeNull();
    expect(ul!.classList.contains("contains-task-list")).toBe(true);

    const items = container.querySelectorAll("li.task-list-item");
    expect(items).toHaveLength(2);
  });

  it("renders the item text beside the checkbox, not the literal `[ ]` markers", () => {
    const { container } = renderBubble(assistantBubble("* [ ] Incomplete\n* [x] Complete"));

    // The bracket markers must be consumed by the parser, not shown as text.
    expect(container.textContent).toContain("Incomplete");
    expect(container.textContent).toContain("Complete");
    expect(container.textContent).not.toContain("[ ]");
    expect(container.textContent).not.toContain("[x]");
  });

  it("leaves plain bullets as plain bullets (no checkbox, no task-list-item class)", () => {
    const { container } = renderBubble(assistantBubble("- plain bullet"));

    expect(container.querySelectorAll('input[type="checkbox"]')).toHaveLength(0);
    const li = container.querySelector("li");
    expect(li).not.toBeNull();
    expect(li!.classList.contains("task-list-item")).toBe(false);
  });

  it("works in the user bubble path (remark-breaks extends, not replaces, remark-gfm)", () => {
    const { container } = renderBubble(userBubble("* [ ] todo\n* [x] done"));

    const checkboxes = container.querySelectorAll('input[type="checkbox"]');
    expect(checkboxes).toHaveLength(2);
    expect(checkboxes[0]!.hasAttribute("checked")).toBe(false);
    expect(checkboxes[1]!.hasAttribute("checked")).toBe(true);
    expect(container.querySelector("ul.contains-task-list")).not.toBeNull();
  });
});
