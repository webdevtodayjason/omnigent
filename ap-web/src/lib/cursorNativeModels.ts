/**
 * Cursor (cursor-sdk) model picker options: the SDK ids the Cursor bridge
 * accepts, paired with friendly display labels. The Cursor SDK rejects a
 * display label like ``Composer`` with an invalid_argument error (``Cannot
 * use this model: Composer. Available models: default, composer-2.5, …``);
 * the picker sends the SDK ``id`` (e.g. ``composer-2.5``) and shows the
 * ``label`` (``Composer``), so a user selection never reaches the SDK as a
 * display label (#547).
 *
 * Static snapshot of the known Cursor SDK models. The robust long-term fix is
 * sourcing the picker options from ``Cursor.models.list()`` (a runner-side
 * query exposed via the session snapshot, mirroring Codex ``model/list``);
 * tracked as a #547 follow-up. When a model retires or a new one ships, this
 * list drifts — refresh it then.
 *
 * Lives in a leaf module (no React / store imports) so both the picker UI
 * (``ChatPage``) and any future store reader can read it without a circular
 * import — same pattern as {@link claudeNativeModels}.
 */
export interface CursorModelOption {
  /** Cursor SDK model id passed to the bridge (e.g. ``"composer-2.5"``). */
  id: string;
  /** Friendly display label shown in the picker (e.g. ``"Composer"``). */
  label: string;
}

// Ordered with the natural defaults first (Cursor's ``default`` auto-select,
// then the Composer flagship), then the frontier models a user would actually
// switch to, most capable first within each family.
export const CURSOR_NATIVE_MODELS: readonly CursorModelOption[] = [
  { id: "default", label: "Default" },
  { id: "composer-2.5", label: "Composer" },
  { id: "claude-opus-4-8", label: "Claude Opus 4.8" },
  { id: "claude-opus-4-7", label: "Claude Opus 4.7" },
  { id: "claude-opus-4-6", label: "Claude Opus 4.6" },
  { id: "claude-opus-4-5", label: "Claude Opus 4.5" },
  { id: "claude-sonnet-4-6", label: "Claude Sonnet 4.6" },
  { id: "claude-sonnet-4-5", label: "Claude Sonnet 4.5" },
  { id: "claude-sonnet-4", label: "Claude Sonnet 4" },
  { id: "claude-haiku-4-5", label: "Claude Haiku 4.5" },
  { id: "gpt-5.5", label: "GPT-5.5" },
  { id: "gpt-5.4", label: "GPT-5.4" },
  { id: "gpt-5.4-mini", label: "GPT-5.4 Mini" },
  { id: "gpt-5.4-nano", label: "GPT-5.4 Nano" },
  { id: "gpt-5.3-codex", label: "GPT-5.3 Codex" },
  { id: "gpt-5.2", label: "GPT-5.2" },
  { id: "gpt-5.2-codex", label: "GPT-5.2 Codex" },
  { id: "gpt-5.1", label: "GPT-5.1" },
  { id: "gpt-5.1-codex-max", label: "GPT-5.1 Codex Max" },
  { id: "gpt-5.1-codex-mini", label: "GPT-5.1 Codex Mini" },
  { id: "gpt-5-mini", label: "GPT-5 Mini" },
  { id: "gemini-3.1-pro", label: "Gemini 3.1 Pro" },
  { id: "gemini-3.5-flash", label: "Gemini 3.5 Flash" },
  { id: "gemini-3-flash", label: "Gemini 3 Flash" },
  { id: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
] as const;

/**
 * Is ``model`` something a Cursor (cursor-sdk) session can actually run —
 * i.e. one of the known Cursor SDK model ids (or a display label this catalog
 * maps)? Accepts the bare SDK ids ({@link CURSOR_NATIVE_MODELS}) and their
 * display labels (case-insensitive). Rejects everything else — notably the
 * Claude / Codex native ids that leak into the cross-harness global picker
 * selection. Mirrors {@link isClaudeNativeModel}; intended for a future
 * cursor sticky-model handoff — the store handoff
 * ({@link nativeModelFamilyForSession}) currently only auto-applies a sticky
 * model to claude/codex native wrappers, so this guard is not yet on the
 * production apply path.
 *
 * @param model - A model id / display label, or null/undefined.
 * @returns True only for a Cursor-compatible model.
 */
export function isCursorNativeModel(model: string | null | undefined): boolean {
  if (model == null) return false;
  const lower = model.toLowerCase();
  return CURSOR_NATIVE_MODELS.some((m) => m.id === model || m.label.toLowerCase() === lower);
}
