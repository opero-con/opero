# Flow Hub — Design Guide

This document records the design decisions, interaction patterns, and CSS conventions
established during the Flow Hub build. Read it before touching the panel.

---

## Philosophy

**Linear-style: minimal, dense, fast.**
Every element earns its space. No decorative borders, no boxes around fields, no
modals where inline editing works. The interface should feel like a focused task tool,
not a form.

---

## Typography

Follow Frappe's own CSS variables — do not invent sizes.

| Role | Token | Approx |
|---|---|---|
| Body / field values | `--text-base` | 13 px |
| Labels / secondary | `--text-sm` | 12 px |
| Metadata / timestamps | `--text-sm` | 12 px |
| Tiny badges only | `--text-xs` | 11 px |

**Never** apply `font-weight: … !important` on a wildcard selector — it flattens all
weight hierarchy and makes text look fuzzy.

**Always pin `font-weight` explicitly on elements that have both a read and an edit
state.** Browser default styles differ between `<h3>` (bold) and `<input>` (inherits),
so without an explicit value the two states look different. Both `.fh-detail__title`
and `.fh-detail__title-input` must declare `font-weight: var(--weight-regular)`.

Add font-smoothing to the root container:

```css
.fh {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
}
```

---

## Property Row Pattern

Fields in the detail panel use a flat label + value row — no outlined fieldsets, no
box borders. This is achieved by scoping overrides under `.fh-detail`:

```
Label        Value text here
Label        Value text here  ×
```

- **Label**: `flex: 0 0 96px`, `--text-sm`, `color: var(--text-muted)`
- **Value**: `flex: 1`, `--text-base`, `color: var(--text-color)`
- **Clickable rows**: `cursor: pointer`; on hover, value text shifts to `var(--primary)` — no border change
- **Clear button (×)**: always present in DOM but `opacity: 0` until hover, then `opacity: 1`

The underlying `fh-field-outlined` markup is preserved (combobox JS depends on it),
but the CSS is scoped to look flat inside `.fh-detail`.

---

## Section Headers

Collapsible: `fh-section-hdr` + `fh-section-body`
Static: `fh-section-label`

- Sentence case only — no `text-transform: uppercase`
- Font: `--text-sm`, semibold, `color: var(--text-muted)`
- Arrow (▶) rotates 90° when open via CSS transition
- Toggle is DOM-only (class swap) — does **not** trigger a full `render()`, so an
  open description editor is never destroyed by collapsing Properties
- Count badge (`fh-section-hdr__count`): small rounded pill, only rendered when
  count > 0

**Attachments always opens collapsed** when switching to a different todo.
`_detail_collapsed` is reset to `{ attachments: true }` at the top of `render()`
whenever `_selected_todo.name !== _rendered_todo_name`. Re-renders on the same todo
preserve whatever the user last set.

---

## Inline Editing — The Click-Away Contract

All inline fields follow this pattern (same as the Project combobox):

1. Click → enter edit mode
2. Edit
3. Click anywhere outside → blur → **auto-save if changed, discard if not**
4. Escape → cancel, revert

**No Save / Cancel buttons for single-field edits.**

Dirty check is mandatory: always compare `draft.value` to `draft.original` before
making an API call. Skip the call if identical.

### Title

- Read mode: `<h3 data-detail-edit-title>` with `cursor: text`
- Edit mode: full-width borderless `<input type="text">`
- Enter → `blur()` → save; Escape → cancel
- Both states must share the same `font-size` and `font-weight` — browser default
  bold on `<h3>` vs regular on `<input>` creates a visible mismatch if not pinned

### Description

- Read mode: plain text extracted from any stored HTML (`_unwrap_quill_html` +
  `textContent`), rendered with `white-space: pre-wrap`
- Edit mode: borderless `<textarea rows="1">` that auto-resizes to content
- `rows="1"` is required — without it the browser defaults to `rows="2"`, causing a
  one-line layout shift on click
- Height is set synchronously after `render()` via JS before the browser paints:
  `ta.style.minHeight = "0"; ta.style.height = "auto"; ta.style.height = ta.scrollHeight + "px"`
- Do **not** use `window.Quill` — it is not exposed as a global in Frappe v15

---

## Meta Row (below the title)

One horizontal row of interactive chips:

```
○  Due today  Open  ↑ Medium
```

| Element | Class | Interaction |
|---|---|---|
| Mark-done circle | `fh-detail__checkbox` | Closes the todo immediately |
| Due date | `fh-meta-chip fh-due-btn fh-due-btn--{band}` | Opens calendar popover |
| Status | `fh-meta-chip fh-status-chip fh-status-chip--{key}` | Opens status dropdown |
| Priority | `fh-meta-chip fh-prio-chip fh-prio-chip--{level}` | Opens priority dropdown |

All chips: `border: none`, tinted background per state, hover darkens one shade.
The status and priority dropdowns reuse the `fh-prio-drop` component pattern.

---

## Assignee Rows

```
Assignee(s)   Patrick W. ★
              Administrator
              + Add
```

- Name always visible, `--text-base`
- **★** (amber, `#f59e0b`) follows the main assignee's name inline — always visible,
  `pointer-events: none`
- Actions (`fh-assignee-row__actions`): `opacity: 0`, fade to `opacity: 1` on row
  hover — contains ◆ (promote) and × (remove)
- Clicking ◆ promotes to main; clicking × removes

---

## Due Date Chips

Color-coded pill with **no border**:

| State | Background | Text |
|---|---|---|
| Overdue | `#fff1f2` | `#ef4444` |
| Due today | `#fff7ed` | `#c2410c` |
| Due soon | `#eff6ff` | `#1d4ed8` |
| Stale | `#f5f3ff` | `#6d28d9` |
| None / empty | transparent | `var(--text-muted)` |

`border: none` must be set explicitly — `<button>` has a browser-default border.

---

## Animations

| Transition | Spec | Notes |
|---|---|---|
| Panel slide-in (first open) | `transform 200ms cubic-bezier(0.25,0.46,0.45,0.94), opacity 160ms ease-out` | Only plays on first open |
| Content fade (every render) | `opacity 0.4→1, translateY 4px→0, 180ms ease-out` | Applied via `@keyframes fh-content-appear` on `.fh-detail__content` |
| Button / chip hover | `background 120ms` | No colour transitions on text |

**Re-renders while the panel is open**: apply `is-detail-open` synchronously (no
rAF), and restore the `scrollTop` of `.fh-detail__content` so saves do not jump
the view. Use `_rendered_todo_name` to detect same-todo re-renders vs. switching.

---

## CSS Architecture

All styles live as a single injected `<style id="fh-styles">` block, written as a
template literal in `_inject_styles()`. Two logical sections:

1. **Base styles** (~lines 80–1560): status bar, chips, queue list, panel chrome,
   popovers, animations
2. **Detail panel overrides** (appended after the responsive block): scoped under
   `.fh-detail` to restyle property rows, section headers, description, assignees

Prefer scoped overrides (`.fh-detail .some-class`) over duplicating rules. The
combobox JS (`_open_link_combobox`) relies on `.fh-field-outlined__body` and
`.fh-field-outlined__value` being present in the DOM — do not remove that markup,
only restyle it.
