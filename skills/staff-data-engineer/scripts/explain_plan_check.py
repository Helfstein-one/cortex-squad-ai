#!/usr/bin/env python3
"""Deterministic static analyzer for PySpark physical execution plans."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ANTI_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "CRITICAL",
        "CartesianProduct detected: replace cross join with keyed equijoin or explicit filter.",
        re.compile(r"\bCartesianProduct\b"),
    ),
    (
        "CRITICAL",
        "BroadcastNestedLoopJoin detected: convert non-equi join to equijoin or bucketed range.",
        re.compile(r"\bBroadcastNestedLoopJoin\b"),
    ),
    (
        "HIGH",
        "Empty PartitionFilters ([]) detected: push down partition predicate to avoid full scan.",
        re.compile(r"PartitionFilters:\s*\[\s*\]"),
    ),
    (
        "HIGH",
        "Python UDF evaluation detected: replace with native Spark SQL / Catalyst expressions.",
        re.compile(r"\b(?:PythonUDF|BatchEvalPython|ArrowEvalPython)\b"),
    ),
    (
        "MEDIUM",
        "CollectLimit detected: avoid global collect/limit before upstream aggregation.",
        re.compile(r"\bCollectLimit\b"),
    ),
]

_UNPARTITIONED_WINDOW_MSG = (
    "Unpartitioned Window detected: specify PARTITION BY keys to avoid single-executor OOM."
)
_SORT_ITEM_RE = re.compile(
    r"\S+\s+(?:(?:ASC|DESC)(?:\s+NULLS\s+(?:FIRST|LAST))?|NULLS\s+(?:FIRST|LAST))\s*$",
    re.IGNORECASE,
)
_EMPTY_BRACKETS_RE = re.compile(r"^\[\s*\]$")
_WINDOW_OP_RE = re.compile(r"\bWindow(?:Exec)?\s*(?=\[)")
_FORMATTED_WINDOW_RE = re.compile(r"(?m)^\s*\*?\(\d+\)\s+Window(?:Exec)?\b[^\n]*(?:\n|$)")
_NEXT_BLOCK_RE = re.compile(r"(?m)^[ \t]*$|^\s*\*?\(\d+\)\s+")
_WINDOW_SPEC_RE = re.compile(r"\bwindowspecdefinition\s*\(", re.IGNORECASE)
_OVER_CLAUSE_RE = re.compile(r"\bOVER\s*\(", re.IGNORECASE)
_NAMED_WINDOW_RE = re.compile(
    r"\bWINDOW\s+(?:[A-Za-z_]\w*|`[^`\n]+`)\s+AS\s*\(", re.IGNORECASE
)
_CHAINED_NAMED_WINDOW_RE = re.compile(
    r"\s*,\s*(?:[A-Za-z_]\w*|`[^`\n]+`)\s+AS\s*\(", re.IGNORECASE
)
_PARTITION_BY_RE = re.compile(r"\bPARTITION\s+BY\b(.*)", re.IGNORECASE | re.DOTALL)
_OVER_BOUNDARY_RE = re.compile(
    r"\b(?:ORDER\s+BY|(?:ROWS|RANGE|GROUPS)\s+(?:BETWEEN|UNBOUNDED|CURRENT|\d))\b",
    re.IGNORECASE,
)
_WINDOW_LINE_RE = re.compile(r"^([ \t|:+-]*)(?:\*?\(\d+\)\s+)?Window(?:Exec)?\s*$")
_LINE_PREFIX_RE = re.compile(r"^([ \t|:+-]*)(.*)$")
_SORT_OR_WRAPPER_RE = re.compile(
    r"^(?:\*?\(\d+\)\s+)?(?:Sort|InputAdapter|AdaptiveSparkPlan|"
    r"AQEShuffleRead|CustomShuffleReader|ShuffleQueryStage)\b"
)
_EXCHANGE_SINGLE_RE = re.compile(r"^(?:\*?\(\d+\)\s+)?Exchange\s+SinglePartition\b")


def _extract_delimited(text: str, open_idx: int, open_ch: str, close_ch: str) -> tuple[str, int]:
    """Return (inner_content, index_after_closing_delimiter) using balanced depth tracking."""
    depth = 0
    quote: str | None = None
    escaped = False
    pos = open_idx
    length = len(text)
    while pos < length:
        ch = text[pos]
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\" and quote != "`":
                escaped = True
            elif ch == quote:
                if quote == "`" and pos + 1 < length and text[pos + 1] == "`":
                    pos += 2
                    continue
                quote = None
        elif ch in ("'", '"', "`"):
            quote = ch
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[open_idx + 1 : pos], pos + 1
        pos += 1
    return text[open_idx + 1 :], length


def _extract_top_level_brackets(text: str, start_idx: int) -> list[str]:
    """Extract consecutive comma-separated top-level [...] groups starting at start_idx."""
    groups: list[str] = []
    pos = start_idx
    length = len(text)
    while pos < length:
        while pos < length and text[pos].isspace():
            pos += 1
        if pos >= length or text[pos] != "[":
            break
        inner, pos = _extract_delimited(text, pos, "[", "]")
        groups.append(inner)
        while pos < length and text[pos].isspace():
            pos += 1
        if pos < length and text[pos] == ",":
            pos += 1
        else:
            break
    return groups


def _split_top_level_csv(text: str) -> list[str]:
    """Split comma-separated items outside nested (), [], and quoted/backticked spans."""
    items: list[str] = []
    paren_depth = 0
    bracket_depth = 0
    quote: str | None = None
    escaped = False
    start = 0
    idx = 0
    length = len(text)
    while idx < length:
        ch = text[idx]
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\" and quote != "`":
                escaped = True
            elif ch == quote:
                if quote == "`" and idx + 1 < length and text[idx + 1] == "`":
                    idx += 2
                    continue
                quote = None
        elif ch in ("'", '"', "`"):
            quote = ch
        elif ch == "(":
            paren_depth += 1
        elif ch == ")" and paren_depth > 0:
            paren_depth -= 1
        elif ch == "[":
            bracket_depth += 1
        elif ch == "]" and bracket_depth > 0:
            bracket_depth -= 1
        elif ch == "," and paren_depth == 0 and bracket_depth == 0:
            item = text[start:idx].strip()
            if item:
                items.append(item)
            start = idx + 1
        idx += 1
    tail = text[start:].strip()
    if tail:
        items.append(tail)
    return items


def _is_sort_order_spec(spec: str) -> bool:
    """Return True if non-empty top-level items in spec are Spark SortOrder expressions."""
    items = _split_top_level_csv(spec)
    return bool(items) and all(_SORT_ITEM_RE.search(item) is not None for item in items)


def _is_window_frame_part(part: str) -> bool:
    """Return True if part is a Spark window frame marker rather than a partition key."""
    lowered = part.strip().lower()
    return (
        lowered.startswith("specifiedwindowframe(")
        or lowered in ("unspecifiedframe$()", "unspecifiedframe")
        or lowered.startswith("unspecifiedframe(")
    )


def _is_window_spec_unpartitioned(expr_group: str) -> bool | None:
    """Inspect windowspecdefinition(...) calls; return True if unpartitioned, None if absent."""
    saw_spec = False
    for match in _WINDOW_SPEC_RE.finditer(expr_group):
        saw_spec = True
        inner, _ = _extract_delimited(expr_group, match.end() - 1, "(", ")")
        parts = [part for part in _split_top_level_csv(inner) if not _is_window_frame_part(part)]
        if not parts or _EMPTY_BRACKETS_RE.match(parts[0]):
            return True
        non_empty = [part for part in parts if not _EMPTY_BRACKETS_RE.match(part)]
        if not non_empty or all(_SORT_ITEM_RE.search(part) is not None for part in non_empty):
            return True
    return False if saw_spec else None


def _mask_quoted_and_comments(text: str) -> str:
    """Mask contents of '...', \"...\", `...` spans and SQL -- / /* */ comments with spaces."""
    chars = list(text)
    length = len(text)
    pos = 0
    no_more_block_close = False
    while pos < length:
        ch = text[pos]
        if ch in ("'", '"', "`"):
            quote = ch
            scan = pos + 1
            closed = False
            while scan < length:
                cur = text[scan]
                if cur == "\\" and quote != "`":
                    scan += 2
                    continue
                if cur == quote:
                    if scan + 1 < length and text[scan + 1] == quote:
                        scan += 2
                        continue
                    closed = True
                    break
                scan += 1
            if closed:
                for idx in range(pos + 1, scan):
                    if chars[idx] != "\n":
                        chars[idx] = " "
                pos = scan + 1
                continue
        elif ch == "-" and pos + 1 < length and text[pos + 1] == "-":
            scan = pos
            while scan < length and text[scan] != "\n":
                chars[scan] = " "
                scan += 1
            pos = scan
            continue
        elif ch == "/" and pos + 1 < length and text[pos + 1] == "*" and not no_more_block_close:
            close_idx = text.find("*/", pos + 2)
            if close_idx != -1:
                for idx in range(pos, close_idx + 2):
                    if chars[idx] != "\n":
                        chars[idx] = " "
                pos = close_idx + 2
                continue
            no_more_block_close = True
            pos += 2
            continue
        pos += 1
    return "".join(chars)


def _mask_nested_parens(text: str) -> str:
    """Replace characters inside nested (...) with spaces so only top-level tokens remain."""
    chars = list(text)
    depth = 0
    for idx, ch in enumerate(chars):
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth > 0:
                depth -= 1
        elif depth > 0 and ch != "\n":
            chars[idx] = " "
    return "".join(chars)


def _spec_lacks_partition_by(inner: str) -> bool:
    """Return True if a SQL window specification lacks a top-level PARTITION BY expression."""
    top_level = _mask_nested_parens(inner)
    part_match = _PARTITION_BY_RE.search(top_level)
    if part_match is None:
        return True
    after_partition = part_match.group(1)
    boundary = _OVER_BOUNDARY_RE.search(after_partition)
    partition_exprs = after_partition[: boundary.start()] if boundary else after_partition
    return not partition_exprs.strip()


def _is_over_clause_unpartitioned(plan_text: str) -> bool:
    """Return True if any SQL OVER (...) or WINDOW w AS (...) lacks a PARTITION BY expression."""
    masked = _mask_quoted_and_comments(plan_text)
    for match in _OVER_CLAUSE_RE.finditer(masked):
        inner, _ = _extract_delimited(masked, match.end() - 1, "(", ")")
        if _spec_lacks_partition_by(inner):
            return True
    for match in _NAMED_WINDOW_RE.finditer(masked):
        inner, next_pos = _extract_delimited(masked, match.end() - 1, "(", ")")
        if _spec_lacks_partition_by(inner):
            return True
        while True:
            chained = _CHAINED_NAMED_WINDOW_RE.match(masked, next_pos)
            if chained is None:
                break
            inner, next_pos = _extract_delimited(masked, chained.end() - 1, "(", ")")
            if _spec_lacks_partition_by(inner):
                return True
    return False


def _has_unbracketed_window_single_partition(plan_text: str) -> bool:
    """Detect unbracketed Window operators sitting directly over Exchange SinglePartition."""
    lines = plan_text.splitlines()
    for idx, line in enumerate(lines):
        win_match = _WINDOW_LINE_RE.match(line)
        if win_match is None:
            continue
        win_prefix = len(win_match.group(1))
        for child_line in lines[idx + 1 :]:
            if not child_line.strip():
                break
            child_match = _LINE_PREFIX_RE.match(child_line)
            if child_match is None:
                break
            child_prefix = len(child_match.group(1))
            if child_prefix <= win_prefix:
                break
            body = child_match.group(2).strip()
            if _EXCHANGE_SINGLE_RE.match(body):
                return True
            if not _SORT_OR_WRAPPER_RE.match(body):
                break
    return False


def _groups_indicate_unpartitioned(groups: list[str]) -> bool:
    """Evaluate extracted top-level Window bracket groups for missing partition keys."""
    if len(groups) >= 3:
        return not groups[1].strip()
    if len(groups) == 2:
        if not groups[1].strip() or _is_sort_order_spec(groups[1]):
            return True
        return _is_window_spec_unpartitioned(groups[0]) is True
    if len(groups) == 1:
        return _is_window_spec_unpartitioned(groups[0]) is True
    return False


def _has_unpartitioned_window(plan_text: str) -> bool:
    """Detect unpartitioned Spark Window operators across single-line, formatted, and SQL plans."""
    if re.search(r"\bWindow\.partitionBy\(\s*\)", plan_text):
        return True
    if re.search(r"\bWindow\b", plan_text) and re.search(r"PartitionSpec:\s*\[\s*\]", plan_text):
        return True
    if _has_unbracketed_window_single_partition(plan_text):
        return True
    if _is_over_clause_unpartitioned(plan_text):
        return True

    for match in _WINDOW_OP_RE.finditer(plan_text):
        groups = _extract_top_level_brackets(plan_text, match.end())
        if _groups_indicate_unpartitioned(groups):
            return True

    for match in _FORMATTED_WINDOW_RE.finditer(plan_text):
        tail = plan_text[match.end() :]
        next_block = _NEXT_BLOCK_RE.search(tail)
        block = tail[: next_block.start()] if next_block else tail
        arg_match = re.search(r"\bArguments:\s*", block)
        if arg_match:
            groups = _extract_top_level_brackets(block, arg_match.end())
            if _groups_indicate_unpartitioned(groups):
                return True
    return False


def analyze_plan(plan_text: str) -> list[tuple[str, str]]:
    """Return a list of (severity, remediation_message) findings for a Spark plan."""
    if not plan_text.strip():
        return [
            (
                "ERROR",
                "Empty execution plan input: pipe Spark explain output via stdin or --file.",
            )
        ]

    findings: list[tuple[str, str]] = []
    for severity, message, pattern in ANTI_PATTERNS:
        if pattern.search(plan_text):
            findings.append((severity, message))
    if _has_unpartitioned_window(plan_text):
        findings.append(("HIGH", _UNPARTITIONED_WINDOW_MSG))
    return findings


def check_plan(plan_text: str) -> bool:
    """Validate a Spark physical execution plan; emit diagnostics and return pass status."""
    findings = analyze_plan(plan_text)
    if findings:
        for severity, message in findings:
            print(f"[{severity}] {message}", file=sys.stderr)
        return False
    print("[OK] Physical execution plan passed static checks.")
    return True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Static analyzer for PySpark physical execution plans."
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Optional path to a text file containing Spark explain output (defaults to stdin).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint returning 0 on clean plan and 1 on findings or read error."""
    args = _build_parser().parse_args(argv)
    if args.file is not None:
        if not args.file.exists():
            print(f"[ERROR] Plan file not found: {args.file}", file=sys.stderr)
            return 1
        try:
            plan_text = args.file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"[ERROR] Failed to read plan file {args.file}: {exc}", file=sys.stderr)
            return 1
    else:
        plan_text = sys.stdin.read() if not sys.stdin.isatty() else ""
    return 0 if check_plan(plan_text) else 1


if __name__ == "__main__":
    sys.exit(main())
