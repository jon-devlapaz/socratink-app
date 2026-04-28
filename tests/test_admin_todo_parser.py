"""Tests for admin.todo_parser — round-trip fidelity, mutation correctness, edge cases."""

from datetime import date

import pytest

from admin.todo_parser import (
    parse_tink_todo,
    toggle_item,
    move_item,
    edit_item_body,
    CANONICAL_BUCKETS,
)


def _items_in_order(doc) -> list[tuple[int, str]]:
    """Helper: list (line_index, body) for every parsed item, in line order."""
    return [(i, doc.items[i].body) for i in sorted(doc.items.keys())]


# --- round-trip + parsing ---

def test_empty_file_round_trips():
    text = ""
    doc = parse_tink_todo(text)
    assert doc.serialize() == text
    assert doc.items == {}


def test_blank_file_with_newline():
    text = "\n"
    doc = parse_tink_todo(text)
    assert doc.serialize() == text


def test_single_item_no_session():
    text = "- [ ] First task\n"
    doc = parse_tink_todo(text)
    assert doc.serialize() == text
    assert len(doc.items) == 1
    item = next(iter(doc.items.values()))
    assert item.is_open is True
    assert item.body == "First task"


def test_session_closeout_with_one_bucket():
    text = (
        "## Session 2026-04-28 Closeout — testing\n"
        "\n"
        "### Now\n"
        "\n"
        "- [ ] First task\n"
        "- [x] Done task\n"
    )
    doc = parse_tink_todo(text)
    assert doc.serialize() == text
    sessions = [s for s in doc.sessions if s.line_index >= 0]
    assert len(sessions) == 1
    assert sessions[0].title == "Session 2026-04-28 Closeout — testing"
    assert len(sessions[0].buckets) == 1
    assert sessions[0].buckets[0].name == "Now"
    assert len(sessions[0].buckets[0].item_lines) == 2


def test_all_five_canonical_buckets():
    text = "## S\n"
    for b in CANONICAL_BUCKETS:
        text += f"### {b}\n- [ ] task in {b}\n"
    doc = parse_tink_todo(text)
    assert doc.serialize() == text
    s = next(s for s in doc.sessions if s.line_index >= 0)
    assert [b.name for b in s.buckets] == list(CANONICAL_BUCKETS)


def test_items_preserve_source_order_within_bucket():
    text = (
        "## S\n"
        "### Now\n"
        "- [ ] alpha\n"
        "- [ ] beta\n"
        "- [ ] gamma\n"
    )
    doc = parse_tink_todo(text)
    s = next(s for s in doc.sessions if s.line_index >= 0)
    bucket = s.buckets[0]
    bodies = [doc.items[idx].body for idx in bucket.item_lines]
    assert bodies == ["alpha", "beta", "gamma"]


def test_resolved_metadata_recognized():
    text = "- [x] foo *(resolved 2026-04-28 by `abc1234`)*\n"
    doc = parse_tink_todo(text)
    item = next(iter(doc.items.values()))
    assert item.is_open is False
    assert item.is_resolved is True
    assert item.is_deprecated is False


def test_deprecated_strikethrough_recognized():
    text = "- [x] ~~foo~~ *(deprecated 2026-04-28 — file removed)*\n"
    doc = parse_tink_todo(text)
    item = next(iter(doc.items.values()))
    assert item.is_open is False
    assert item.is_deprecated is True
    assert item.is_resolved is False


def test_builders_trap_flag_recognized():
    text = "- [ ] Refactor X *(Builder's Trap? → ties to June 2026 goal how?)*\n"
    doc = parse_tink_todo(text)
    item = next(iter(doc.items.values()))
    assert item.is_builders_trap is True


def test_nested_children_tracked():
    text = (
        "- [ ] Parent task\n"
        "  - [ ] Child A\n"
        "  - [ ] Child B\n"
        "- [ ] Sibling\n"
    )
    doc = parse_tink_todo(text)
    assert doc.serialize() == text
    parent = next(i for i in doc.items.values() if i.body == "Parent task")
    child_a = next(i for i in doc.items.values() if i.body == "Child A")
    child_b = next(i for i in doc.items.values() if i.body == "Child B")
    sibling = next(i for i in doc.items.values() if i.body == "Sibling")
    assert child_a.parent == parent.line_index
    assert child_b.parent == parent.line_index
    assert sibling.parent is None
    assert sorted(parent.children) == sorted(
        [child_a.line_index, child_b.line_index]
    )


def test_session_with_no_buckets_treated_as_top_bucket():
    text = (
        "## S no buckets\n"
        "- [ ] direct under session\n"
    )
    doc = parse_tink_todo(text)
    assert doc.serialize() == text
    s = next(s for s in doc.sessions if s.line_index >= 0)
    assert len(s.buckets) == 1
    assert s.buckets[0].name == "(top)"
    assert len(s.buckets[0].item_lines) == 1


def test_prose_paragraphs_preserved_round_trip():
    text = (
        "- [ ] first\n"
        "\n"
        "## Session\n"
        "\n"
        "Plan doc: see somewhere. *Builder's Trap? → No.*\n"
        "\n"
        "### Now\n"
        "- [ ] task after prose\n"
    )
    doc = parse_tink_todo(text)
    assert doc.serialize() == text


def test_complex_real_file_round_trip():
    """Parser must round-trip the actual production todo.md without mutation."""
    with open("/Users/jondev/dev/socratink/todo.md") as f:
        text = f.read()
    doc = parse_tink_todo(text)
    assert doc.serialize() == text


# --- mutation: toggle ---

def test_toggle_open_to_closed_appends_admin_toggle_meta():
    text = "- [ ] foo\n"
    doc = parse_tink_todo(text)
    line = next(iter(doc.items.keys()))
    toggle_item(doc, line, today=date(2026, 4, 28))
    assert doc.lines[line] == "- [x] foo *(resolved 2026-04-28 by admin-toggle)*"
    assert "*(resolved 2026-04-28 by admin-toggle)*" in doc.serialize()


def test_toggle_closed_to_open_strips_admin_toggle_meta():
    text = "- [x] foo *(resolved 2026-04-28 by admin-toggle)*\n"
    doc = parse_tink_todo(text)
    line = next(iter(doc.items.keys()))
    toggle_item(doc, line, today=date(2026, 4, 28))
    assert doc.lines[line] == "- [ ] foo"


def test_toggle_open_with_existing_resolved_meta_keeps_it():
    """If somehow [ ] open with prior resolved meta (uncommon), don't double-stamp."""
    text = "- [ ] foo *(resolved 2025-01-01 by `oldsha1`)*\n"
    doc = parse_tink_todo(text)
    line = next(iter(doc.items.keys()))
    toggle_item(doc, line, today=date(2026, 4, 28))
    assert doc.lines[line] == "- [x] foo *(resolved 2025-01-01 by `oldsha1`)*"
    assert "admin-toggle" not in doc.lines[line]


def test_toggle_closed_with_real_commit_metadata_preserves_meta():
    """Re-opening a real-commit-resolved item only strips admin-toggle, not real meta."""
    text = "- [x] foo *(resolved 2025-01-01 by `realcommit`)*\n"
    doc = parse_tink_todo(text)
    line = next(iter(doc.items.keys()))
    toggle_item(doc, line, today=date(2026, 4, 28))
    # admin-toggle pattern not present, so re-open keeps the original metadata
    assert doc.lines[line] == "- [ ] foo *(resolved 2025-01-01 by `realcommit`)*"


# --- mutation: move ---

def test_move_item_within_bucket_to_top():
    text = (
        "## S\n"
        "### Now\n"
        "- [ ] alpha\n"
        "- [ ] beta\n"
        "- [ ] gamma\n"
    )
    doc = parse_tink_todo(text)
    bucket = next(s for s in doc.sessions if s.line_index >= 0).buckets[0]
    gamma_line = bucket.item_lines[2]
    bucket_line = bucket.line_index
    move_item(doc, line_index=gamma_line, target_bucket_line=bucket_line, after_item_line=None)
    s_re = next(s for s in doc.sessions if s.line_index >= 0)
    bodies = [doc.items[idx].body for idx in s_re.buckets[0].item_lines]
    assert bodies == ["gamma", "alpha", "beta"]


def test_move_item_between_buckets_in_same_session():
    text = (
        "## S\n"
        "### Now\n"
        "- [ ] alpha\n"
        "### Backlog\n"
        "- [ ] beta\n"
    )
    doc = parse_tink_todo(text)
    s = next(s for s in doc.sessions if s.line_index >= 0)
    backlog = s.buckets[1]
    beta_line = backlog.item_lines[0]
    now_bucket_line = s.buckets[0].line_index
    move_item(doc, line_index=beta_line, target_bucket_line=now_bucket_line, after_item_line=None)
    s_re = next(s for s in doc.sessions if s.line_index >= 0)
    now_bodies = [doc.items[idx].body for idx in s_re.buckets[0].item_lines]
    backlog_bodies = [doc.items[idx].body for idx in s_re.buckets[1].item_lines]
    assert now_bodies == ["beta", "alpha"]
    assert backlog_bodies == []


def test_move_item_with_children_keeps_children_attached():
    text = (
        "## S\n"
        "### Now\n"
        "- [ ] alpha\n"
        "- [ ] parent\n"
        "  - [ ] child A\n"
        "  - [ ] child B\n"
        "- [ ] gamma\n"
    )
    doc = parse_tink_todo(text)
    bucket = next(s for s in doc.sessions if s.line_index >= 0).buckets[0]
    parent_line = next(idx for idx in bucket.item_lines if doc.items[idx].body == "parent")
    bucket_line = bucket.line_index
    move_item(doc, line_index=parent_line, target_bucket_line=bucket_line, after_item_line=None)
    s_re = next(s for s in doc.sessions if s.line_index >= 0)
    new_bucket = s_re.buckets[0]
    bodies = [doc.items[idx].body for idx in new_bucket.item_lines]
    assert bodies == ["parent", "alpha", "gamma"]
    parent_re = next(i for i in doc.items.values() if i.body == "parent")
    assert len(parent_re.children) == 2


# --- mutation: edit ---

def test_edit_body_preserves_indent_and_checkbox():
    text = (
        "## S\n"
        "### Now\n"
        "  - [x] old body *(resolved 2026-04-28 by `abc`)*\n"
    )
    doc = parse_tink_todo(text)
    line = next(iter(doc.items.keys()))
    edit_item_body(doc, line, "fresh body *(resolved 2026-04-28 by `abc`)*")
    assert doc.lines[line] == "  - [x] fresh body *(resolved 2026-04-28 by `abc`)*"
    assert doc.serialize().endswith("`abc`)*\n")


def test_edit_body_rejects_newline():
    text = "- [ ] foo\n"
    doc = parse_tink_todo(text)
    line = next(iter(doc.items.keys()))
    with pytest.raises(ValueError, match="single-line"):
        edit_item_body(doc, line, "first\nsecond")


def test_edit_body_rejects_empty():
    text = "- [ ] foo\n"
    doc = parse_tink_todo(text)
    line = next(iter(doc.items.keys()))
    with pytest.raises(ValueError, match="cannot be empty"):
        edit_item_body(doc, line, "   ")


def test_edit_body_rejects_non_item_line():
    text = "## Heading\n- [ ] foo\n"
    doc = parse_tink_todo(text)
    with pytest.raises(KeyError):
        edit_item_body(doc, 0, "anything")


def test_move_across_sessions_raises():
    text = (
        "## S1\n"
        "### Now\n"
        "- [ ] alpha\n"
        "## S2\n"
        "### Now\n"
        "- [ ] beta\n"
    )
    doc = parse_tink_todo(text)
    sessions = [s for s in doc.sessions if s.line_index >= 0]
    alpha_line = sessions[0].buckets[0].item_lines[0]
    s2_now_line = sessions[1].buckets[0].line_index
    with pytest.raises(ValueError, match="across Session Closeouts"):
        move_item(doc, line_index=alpha_line, target_bucket_line=s2_now_line)
