"""Pure-function parser + line-aware mutator for the Tink TODO file.

Round-trip fidelity: parse(text) → serialize() returns byte-identical text
when no mutations have been applied. Mutations are line-level rewrites
(toggle) or multi-line cut+insert (move) that preserve all surrounding
context (prose paragraphs, blank lines, lessons sections).

Glossary terms (per docs/pipeline/_meta/CONTEXT.md):
    - Tink TODO        — the markdown file
    - TODO Item        — `- [ ]` or `- [x]` line, possibly indented (sub-child)
    - Bucket           — h3 section: Now, Next, Backlog, Housekeeping, Lessons
    - Session Closeout — h2 heading
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

H2_RE = re.compile(r"^(##) (.+)$")
H3_RE = re.compile(r"^(###) (.+)$")
ITEM_RE = re.compile(r"^(\s*)- \[( |x)\] (.*)$")
ADMIN_TOGGLE_META_RE = re.compile(
    r"\s*\*\(resolved \d{4}-\d{2}-\d{2} by admin-toggle\)\*"
)
RESOLVED_RE = re.compile(r"\*\(resolved \d{4}-\d{2}-\d{2}[^)]*\)\*")
DEPRECATED_RE = re.compile(r"\*\(deprecated \d{4}-\d{2}-\d{2}[^)]*\)\*")
BUILDERS_TRAP_RE = re.compile(r"\*\(Builder's Trap\? → [^)]*\)\*")
STRIKE_RE = re.compile(r"~~(.+?)~~")

CANONICAL_BUCKETS: tuple[str, ...] = (
    "Now",
    "Next",
    "Backlog",
    "Housekeeping",
    "Lessons",
)


@dataclass
class Item:
    line_index: int
    indent: int
    is_open: bool
    body: str
    children: list[int] = field(default_factory=list)
    parent: int | None = None

    @property
    def is_resolved(self) -> bool:
        return not self.is_open and bool(RESOLVED_RE.search(self.body))

    @property
    def is_deprecated(self) -> bool:
        return not self.is_open and bool(DEPRECATED_RE.search(self.body))

    @property
    def is_builders_trap(self) -> bool:
        return bool(BUILDERS_TRAP_RE.search(self.body))


@dataclass
class Bucket:
    line_index: int            # -1 for the implicit pre-bucket region of a session
    name: str
    item_lines: list[int] = field(default_factory=list)


@dataclass
class Session:
    line_index: int            # -1 for the implicit top-level (before first ##)
    title: str
    buckets: list[Bucket] = field(default_factory=list)


@dataclass
class TodoDocument:
    lines: list[str]
    sessions: list[Session]
    items: dict[int, Item]
    _trailing_newline: bool = True

    def serialize(self) -> str:
        out = "\n".join(self.lines)
        if self._trailing_newline:
            out += "\n"
        return out

    def public_dict(self) -> dict:
        """Structured representation for JSON serialization to the client."""
        return {
            "sessions": [
                {
                    "line_index": s.line_index,
                    "title": s.title,
                    "buckets": [
                        {
                            "line_index": b.line_index,
                            "name": b.name,
                            "items": [
                                _item_dict(self.items[idx], self.lines[idx])
                                for idx in b.item_lines
                            ],
                        }
                        for b in s.buckets
                    ],
                }
                for s in self.sessions
            ],
        }


def _item_dict(item: Item, raw_line: str) -> dict:
    body_no_strike = STRIKE_RE.sub(r"\1", item.body)
    return {
        "line_index": item.line_index,
        "indent": item.indent,
        "is_open": item.is_open,
        "is_resolved": item.is_resolved,
        "is_deprecated": item.is_deprecated,
        "is_builders_trap": item.is_builders_trap,
        "body": item.body,
        "body_plain": body_no_strike,
        "raw": raw_line,
        "children": [
            {
                "line_index": c,
                "raw": "",
            }
            for c in item.children
        ],
    }


def parse_tink_todo(text: str) -> TodoDocument:
    trailing_newline = text.endswith("\n")
    lines = text.splitlines()

    items: dict[int, Item] = {}
    sessions: list[Session] = []

    top_session = Session(line_index=-1, title="(top-level)")
    sessions.append(top_session)
    current_session = top_session
    current_bucket: Bucket | None = None
    indent_stack: list[tuple[int, int]] = []  # (indent, line_index)

    def _ensure_bucket() -> Bucket:
        nonlocal current_bucket
        if current_bucket is None:
            current_bucket = Bucket(line_index=-1, name="(top)")
            current_session.buckets.append(current_bucket)
        return current_bucket

    for i, line in enumerate(lines):
        if h2 := H2_RE.match(line):
            current_session = Session(line_index=i, title=h2.group(2))
            sessions.append(current_session)
            current_bucket = None
            indent_stack.clear()
            continue
        if h3 := H3_RE.match(line):
            current_bucket = Bucket(line_index=i, name=h3.group(2))
            current_session.buckets.append(current_bucket)
            indent_stack.clear()
            continue
        if im := ITEM_RE.match(line):
            indent_str, checkbox, body = im.groups()
            indent = len(indent_str)
            item = Item(
                line_index=i,
                indent=indent,
                is_open=(checkbox == " "),
                body=body,
            )
            items[i] = item
            while indent_stack and indent_stack[-1][0] >= indent:
                indent_stack.pop()
            if indent_stack:
                parent_idx = indent_stack[-1][1]
                items[parent_idx].children.append(i)
                item.parent = parent_idx
            else:
                bkt = _ensure_bucket()
                bkt.item_lines.append(i)
            indent_stack.append((indent, i))
            continue
        if line.strip() == "":
            indent_stack.clear()

    return TodoDocument(
        lines=lines,
        sessions=sessions,
        items=items,
        _trailing_newline=trailing_newline,
    )


def toggle_item(doc: TodoDocument, line_index: int, *, today: date) -> None:
    """Flip an item open<->closed.

    Closed → open: strip the `admin-toggle` resolved-metadata if present.
    Open → closed: append `*(resolved YYYY-MM-DD by admin-toggle)*` if not
    already carrying a `*(resolved ...)*` annotation. Existing annotations
    (e.g., closed by a real commit) are left intact.
    """
    if line_index not in doc.items:
        raise KeyError(f"line {line_index} is not a TODO Item")
    line = doc.lines[line_index]
    m = ITEM_RE.match(line)
    if not m:
        raise ValueError(f"line {line_index} is not an item: {line!r}")
    indent_str, checkbox, body = m.groups()
    if checkbox == " ":
        body = body.rstrip()
        if not RESOLVED_RE.search(body):
            body = f"{body} *(resolved {today.isoformat()} by admin-toggle)*"
        new_line = f"{indent_str}- [x] {body}"
    else:
        body = ADMIN_TOGGLE_META_RE.sub("", body).rstrip()
        new_line = f"{indent_str}- [ ] {body}"
    doc.lines[line_index] = new_line
    item = doc.items[line_index]
    item.is_open = (checkbox != " ")
    item.body = body


def edit_item_body(doc: TodoDocument, line_index: int, new_body: str) -> None:
    """Replace an item's body, preserving the indent and checkbox state.

    The body is taken verbatim — metadata annotations (`*(resolved ...)*`,
    `*(deprecated ...)*`, `*(Builder's Trap? ...)*`, `~~strike~~`) are
    whatever the caller passed. The dashboard sends the raw body so the
    user can choose to keep, edit, or remove annotations.
    """
    if line_index not in doc.items:
        raise KeyError(f"line {line_index} is not a TODO Item")
    if "\n" in new_body or "\r" in new_body:
        raise ValueError("item body must be single-line")
    if not new_body.strip():
        raise ValueError("item body cannot be empty")
    line = doc.lines[line_index]
    m = ITEM_RE.match(line)
    if not m:
        raise ValueError(f"line {line_index} is not an item: {line!r}")
    indent_str, checkbox, _ = m.groups()
    doc.lines[line_index] = f"{indent_str}- [{checkbox}] {new_body}"
    doc.items[line_index].body = new_body


def _item_block(doc: TodoDocument, line_index: int) -> tuple[int, int]:
    """Return (start, end_exclusive) line range for an item plus its children."""
    if line_index not in doc.items:
        raise KeyError(f"line {line_index} is not a TODO Item")
    item = doc.items[line_index]
    indent = item.indent
    end = line_index + 1
    while end < len(doc.lines):
        nxt = doc.lines[end]
        m = ITEM_RE.match(nxt)
        if m and len(m.group(1)) > indent:
            end += 1
            continue
        break
    return line_index, end


def _session_for_item(doc: TodoDocument, line_index: int) -> Session:
    item_line = line_index
    candidate = doc.sessions[0]
    for s in doc.sessions:
        if s.line_index == -1:
            continue
        if s.line_index < item_line:
            candidate = s
        else:
            break
    return candidate


def move_item(
    doc: TodoDocument,
    *,
    line_index: int,
    target_bucket_line: int,
    after_item_line: int | None = None,
) -> None:
    """Move an item (with its children) to a target bucket position.

    target_bucket_line: line index of the destination bucket's h3 heading,
        OR -1 to address the implicit top-of-session bucket.
    after_item_line: line index of the existing item to position AFTER.
        None = insert at the start of the bucket (after the h3 heading line,
        or at the start of session if bucket is implicit).

    Constraint: source and target must be in the same Session Closeout.
    Cross-session moves raise ValueError.
    """
    if line_index not in doc.items:
        raise KeyError(f"line {line_index} is not a TODO Item")
    src_session = _session_for_item(doc, line_index)
    if target_bucket_line == -1:
        dst_session = src_session
    else:
        dst_session = _session_for_line(doc, target_bucket_line)
    if src_session.line_index != dst_session.line_index:
        raise ValueError(
            "move across Session Closeouts is not supported "
            f"(src={src_session.line_index}, dst={dst_session.line_index})"
        )

    start, end = _item_block(doc, line_index)
    block = doc.lines[start:end]

    if after_item_line is not None:
        if after_item_line not in doc.items:
            raise KeyError(f"after_item_line {after_item_line} is not a TODO Item")
        _, after_end = _item_block(doc, after_item_line)
        insert_at = after_end
    elif target_bucket_line == -1:
        insert_at = (
            src_session.line_index + 1
            if src_session.line_index >= 0
            else 0
        )
    else:
        insert_at = target_bucket_line + 1

    if start <= insert_at < end:
        raise ValueError("cannot move an item into itself or its own subtree")

    # remove block, then insert at adjusted position
    new_lines = doc.lines[:start] + doc.lines[end:]
    if insert_at > end:
        insert_at -= (end - start)
    elif insert_at >= start:
        insert_at = start
    new_lines = new_lines[:insert_at] + block + new_lines[insert_at:]

    rebuilt = parse_tink_todo("\n".join(new_lines) + ("\n" if doc._trailing_newline else ""))
    doc.lines = rebuilt.lines
    doc.sessions = rebuilt.sessions
    doc.items = rebuilt.items


def _session_for_line(doc: TodoDocument, line_index: int) -> Session:
    candidate = doc.sessions[0]
    for s in doc.sessions:
        if s.line_index == -1:
            continue
        if s.line_index <= line_index:
            candidate = s
        else:
            break
    return candidate
