#!/usr/bin/env python3
"""fxclip core normalizer.
Deterministic text reconstruction for terminal-wrapped clipboard content.
"""

from __future__ import annotations

import re
import statistics
import sys
from dataclasses import dataclass
from typing import Iterable, List, Optional

RE_LIST = re.compile(r"^\s*([-*•]|\d+[.)])\s+")
RE_FENCE = re.compile(r"^\s*```")
RE_HEADING_COLON = re.compile(r"^\s*[A-Z][^:]{1,120}:\s*$")
RE_NUM_HEAD = re.compile(r"^\s*\d+[.)]\s+(.*)$")
RE_WORD_LOWER = re.compile(r"^[a-z]")
RE_WORD_ALNUM = re.compile(r"^[A-Za-z0-9]")

CONNECTORS = {
    "and", "or", "to", "of", "for", "with", "in", "on", "at", "from", "by",
    "as", "than", "that", "which", "who",
}


@dataclass
class Stats:
    in_lines: int
    out_lines: int
    list_hits: int
    code_hits: int
    table_hits: int


def is_list(s: str) -> bool:
    return bool(RE_LIST.match(s))


def is_fence(s: str) -> bool:
    return bool(RE_FENCE.match(s))


def is_table(s: str) -> bool:
    return ("|" in s) or ("\t" in s)


def is_numbered_heading(s: str) -> bool:
    m = RE_NUM_HEAD.match(s)
    if not m:
        return False
    body = m.group(1).strip()
    if not body:
        return False
    words = body.split()
    if len(words) > 14:
        return False
    if body.endswith(":") or body.endswith(")"):
        return True
    if "(" in body and ")" in body:
        return True
    titleish = sum(1 for w in words if re.match(r"^[A-Z]", w))
    return titleish >= max(1, len(words) // 2)


def is_heading(s: str) -> bool:
    return bool(RE_HEADING_COLON.match(s)) or is_numbered_heading(s)


def _split_collapsed_heading(line: str) -> List[str]:
    s = line.strip()
    m = re.match(r"^(\d+[.)]\s+.+\([^)]*\))\s+([A-Z].+)$", s)
    if m:
        head = m.group(1).strip()
        body = m.group(2).strip()
        if is_heading(head):
            return [head, body]
    return [line]


def _split_inline_code_to_prose(line: str) -> List[str]:
    s = line.strip()
    if not s:
        return [line]

    m = re.match(
        r"^(.*(?:def|class|return|if|for|while|print)\b.*?\S)\s+(This|That|Then|After|Next|Here|Now)\b(.*)$",
        s,
    )
    if m:
        return [m.group(1).strip(), (m.group(2) + m.group(3)).strip()]

    m = re.match(r"^(.*[\]\)\}\"'\d])\s+([A-Z][a-z].*)$", s)
    if m and re.search(r"[\[\]\(\)=+\-*/]|\breturn\b|\bdef\b|\bclass\b", m.group(1)):
        return [m.group(1).strip(), m.group(2).strip()]

    return [line]


def _recover_space_wrapped_blob(text: str) -> str:
    if "\n" in text:
        return text
    gaps = re.findall(r" {3,}", text)
    if len(gaps) < 3:
        return text
    parts = [p.strip() for p in re.split(r" {3,}", text) if p.strip()]
    if len(parts) < 3:
        return text
    return "\n".join(parts)


def _estimate_wrap_width(lines: List[str]) -> Optional[int]:
    lens = [len(x.strip()) for x in lines if len(x.strip()) >= 20]
    if len(lens) < 3:
        return None
    med = int(statistics.median(lens))
    if med < 30:
        return None
    spread = max(lens) - min(lens)
    if spread > max(35, med // 2):
        return None
    return med


def _boundary_score(prev_line: str, next_line: str, wrap_width: Optional[int]) -> int:
    score = 0

    if re.search(r"([A-Za-z0-9])-$", prev_line) and RE_WORD_ALNUM.match(next_line):
        return 100

    if RE_WORD_LOWER.match(next_line):
        score += 3
    if re.search(r"[,;]$", prev_line):
        score += 2
    if re.search(r"\b(" + "|".join(CONNECTORS) + r")$", prev_line):
        score += 2
    if len(prev_line) >= 72 and not re.search(r"[.!?:)]$", prev_line):
        score += 1
    if re.match(r"^[\(\[]?[a-z0-9]", next_line):
        score += 1

    if wrap_width is not None and len(prev_line) >= max(20, wrap_width - 6):
        score += 5
        if re.match(r"^[A-Z]", next_line):
            score += 1

    if re.search(r"[.!?]$", prev_line):
        score -= 4
    if re.search(r"\b(def|class|return|if|for|while|print)\b", prev_line) and re.match(
        r"^(This|That|Then|After|Next|Here|Now)\b", next_line
    ):
        score -= 8
    if is_list(next_line):
        score -= 5
    if RE_HEADING_COLON.match(next_line):
        score -= 3
    if re.match(r"^\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4}$", next_line):
        score -= 2

    return score


def join_wrapped(chunk: Iterable[str]) -> str:
    lines = [x.strip() for x in chunk if x is not None and x.strip() != ""]
    if not lines:
        return ""
    if len(lines) == 1:
        return lines[0]

    if is_heading(lines[0]) and len(lines) > 1:
        body = join_wrapped(lines[1:])
        return lines[0] if not body else f"{lines[0]}\n{body}"

    wrap_width = _estimate_wrap_width(lines)
    out = lines[0]
    for nxt in lines[1:]:
        score = _boundary_score(out, nxt, wrap_width)
        join = score > 0
        no_space = score >= 100

        if join:
            if no_space:
                out = re.sub(r"-$", "", out) + nxt
            else:
                out += " " + nxt
        else:
            out += "\n" + nxt

    out = re.sub(r"[ \t]{2,}", " ", out).strip()
    out = re.sub(r"([a-z0-9][.!?])([A-Z])", r"\1 \2", out)
    return out


def _can_continue_list_item(last_block: str, line: str) -> bool:
    if not is_list(last_block):
        return False
    if is_heading(last_block):
        return False

    s = line.strip()
    if not s:
        return False
    if is_list(s) or is_table(s) or is_heading(s) or is_fence(s):
        return False
    if re.match(r"^[a-z(\[]", s):
        return True
    if re.search(r"[,;:-]$", last_block.strip()):
        return True
    if len(last_block.strip()) >= 48 and not re.search(r"[.!?]$", last_block.strip()):
        return True
    return False


def _is_structural_line(s: str) -> bool:
    t = s.strip()
    return is_heading(t) or is_list(t) or is_table(t) or is_fence(t)


def _insert_paragraph_spacing(out: str) -> str:
    if not out:
        return out
    src = out.split("\n")
    dst: List[str] = []
    for line in src:
        if (
            dst
            and line.strip()
            and dst[-1].strip()
            and _is_structural_line(line)
            and not is_fence(line.strip())
            and not _is_structural_line(dst[-1])
        ):
            dst.append("")
        dst.append(line)
    return "\n".join(dst)


def _compact_noncode_whitespace(out: str) -> str:
    if not out:
        return out
    src = out.split("\n")
    dst: List[str] = []
    in_code = False
    for line in src:
        t = line.rstrip()
        if is_fence(t.strip()):
            dst.append(t)
            in_code = not in_code
            continue
        if in_code:
            dst.append(t)
            continue
        compact = re.sub(r"[ \t]{2,}", " ", t)
        compact = re.sub(r"([a-z0-9][.!?])([A-Z])", r"\1 \2", compact)
        compact = re.sub(r"(?<=[A-Za-z])-\s+(?=[a-z])", "-", compact)
        dst.append(compact.strip() if compact.strip() else "")
    return "\n".join(dst)


def _explode_inline_list_markers(out: str) -> str:
    """Split inline sentence+list patterns into dedicated list lines."""
    if not out:
        return out
    src = out.split("\n")
    dst: List[str] = []
    in_code = False
    for line in src:
        t = line.rstrip()
        if is_fence(t.strip()):
            dst.append(t)
            in_code = not in_code
            continue
        if in_code:
            dst.append(t)
            continue

        # Example:
        # "... paragraph. - bullet one. - bullet two"
        t = re.sub(r"([.!?])\s+([-*•]|\d+[.)])\s+", r"\1\n\2 ", t)
        dst.extend(t.split("\n"))
    return "\n".join(dst)


def _explode_inline_structural_markers(out: str) -> str:
    """Split collapsed mixed-content lines into structural lines."""
    if not out:
        return out
    src = out.split("\n")
    dst: List[str] = []
    in_code = False

    for line in src:
        t = line.rstrip()
        if t.strip() == "":
            dst.append("")
            continue

        if is_fence(t.strip()):
            dst.append(t)
            in_code = not in_code
            continue
        if in_code:
            dst.append(t)
            continue

        # Heading with inline body: "Summary: text..."
        m = re.match(r"^\s*([A-Z][^:]{1,120}:)\s+(.+)$", t)
        if m:
            dst.append(m.group(1).strip())
            t = m.group(2).strip()

        # Sentence -> inline heading boundary.
        t = re.sub(r"([.!?])\s+([A-Z][A-Za-z0-9/&()\- ]{1,80}:)\s+", r"\1\n\2\n", t)

        # Split before inline code fence marker.
        t = re.sub(r"\s+(```\w*)\s+", r"\n\1\n", t)

        # Split fence + code if collapsed: "```python def ...".
        m2 = re.match(r"^\s*(```\w*)\s+(.+)$", t)
        if m2:
            dst.append(m2.group(1).strip())
            t = m2.group(2).strip()

        # Try to split compacted table rows:
        # "A | B | C 1 | 2 | 3 4 | 5 | 6"
        if t.count("|") >= 4:
            t = re.sub(r"([.!?])\s+([A-Za-z]\s*\|[^|]+\|[^|]+)", r"\1\n\2", t)
            t = re.sub(r"(?<!\|)\s+(?=\d+\s*\|)", "\n", t)

        # Code-like tail followed by prose sentence.
        t = re.sub(
            r"(\breturn\b[^\n]*?\S)\s+(?=(This|That|Then|After|Next|Here|Now)\b)",
            r"\1\n",
            t,
        )

        for part in t.split("\n"):
            if part.strip() == "":
                dst.append("")
            else:
                dst.append(part.strip())

    return "\n".join(dst)


def _split_list_tail_prose(out: str) -> str:
    """Split merged 'list sentence + trailing prose' into separate lines."""
    if not out:
        return out
    src = out.split("\n")
    dst: List[str] = []
    in_code = False
    # If tail starts with these, it's likely same sentence continuation.
    cont_words = r"(?:and|or|to|of|for|with|in|on|at|from|by|as|than|that|which|who)"
    pat = re.compile(
        rf"^(\s*([-*•]|\d+[.)])\s+.+?[.!?])\s+(?!{cont_words}\b)([a-z].+)$"
    )
    for line in src:
        t = line.rstrip()
        if is_fence(t.strip()):
            dst.append(t)
            in_code = not in_code
            continue
        if in_code:
            dst.append(t)
            continue
        m = pat.match(t)
        if m:
            dst.append(m.group(1).strip())
            dst.append(m.group(3).strip())
        else:
            dst.append(t)
    return "\n".join(dst)


def normalize_text(text: str) -> tuple[str, Stats]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00A0", " ")
    text = _recover_space_wrapped_blob(text)
    lines = text.split("\n")

    fence_total = sum(1 for raw in lines if is_fence(raw.strip()))
    fenced_mode = fence_total % 2 == 0

    blocks: List[str] = []
    para: List[str] = []
    in_code = False

    def flush_para() -> None:
        nonlocal para
        if para:
            joined = join_wrapped(para)
            if joined.strip():
                blocks.append(joined)
            para = []

    for raw in lines:
        line = re.sub(r"\s+$", "", raw)

        expanded: List[str] = []
        for x in _split_collapsed_heading(line):
            expanded.extend(_split_inline_code_to_prose(x))

        for line in expanded:
            line = re.sub(r"\s+$", "", line)

            if is_fence(line):
                flush_para()
                blocks.append(line)
                if fenced_mode:
                    in_code = not in_code
                continue

            if in_code:
                blocks.append(line)
                continue

            if line.strip() == "":
                flush_para()
                if not blocks or blocks[-1] != "":
                    blocks.append("")
                continue

            if is_heading(line):
                flush_para()
                blocks.append(line.rstrip())
                continue

            if is_list(line) or is_table(line):
                flush_para()
                blocks.append(line.rstrip())
                continue

            if blocks and _can_continue_list_item(blocks[-1], line):
                blocks[-1] = f"{blocks[-1].rstrip()} {line.strip()}"
                blocks[-1] = re.sub(r"[ \t]{2,}", " ", blocks[-1]).rstrip()
                continue

            para.append(line)

    flush_para()

    final: List[str] = []
    prev_blank = False
    for b in blocks:
        blank = b.strip() == ""
        if blank and prev_blank:
            continue
        final.append(b)
        prev_blank = blank

    out = "\n".join(final).strip()
    out = re.sub(r"([a-z0-9][.!?])([A-Z])", r"\1 \2", out)
    out = _insert_paragraph_spacing(out)
    out = _compact_noncode_whitespace(out)
    out = _explode_inline_list_markers(out)
    out = _explode_inline_structural_markers(out)
    out = _split_list_tail_prose(out)
    out = _insert_paragraph_spacing(out)

    stats = Stats(
        in_lines=len(lines),
        out_lines=0 if out == "" else out.count("\n") + 1,
        list_hits=sum(1 for s in lines if is_list(s)),
        code_hits=sum(1 for s in lines if is_fence(s)),
        table_hits=sum(1 for s in lines if is_table(s)),
    )
    return out, stats


def main() -> int:
    text = sys.stdin.read()
    out, _ = normalize_text(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
