#!/usr/bin/env python3
from fxclip_core import normalize_text

CASES = [
    (
        "wrapped prose",
        "This is a deliberately long paragraph copied from a narrow terminal\nwindow where each visual row was wrapped by viewport width and should\nbecome a single continuous line after running fxclip.",
        "This is a deliberately long paragraph copied from a narrow terminal window where each visual row was wrapped by viewport width and should become a single continuous line after running fxclip.",
    ),
    (
        "numbered heading + body",
        "1. Wrapped prose (should become one line)\nThis is a deliberately long paragraph copied from a narrow terminal\nwindow and this body should become one line but stay under the heading.",
        "1. Wrapped prose (should become one line)\nThis is a deliberately long paragraph copied from a narrow terminal window and this body should become one line but stay under the heading.",
    ),
    (
        "collapsed heading/body recovered",
        "1. Wrapped prose (should become one line) This is a deliberately long paragraph copied from a narrow terminal window and should be placed on the next line as body text.",
        "1. Wrapped prose (should become one line)\nThis is a deliberately long paragraph copied from a narrow terminal window and should be placed on the next line as body text.",
    ),
    (
        "list preserved",
        "1. first item\n2. second item\n3. third item",
        "1. first item\n2. second item\n3. third item",
    ),
    (
        "bullet list preserved",
        "- alpha\n- beta\n- gamma",
        "- alpha\n- beta\n- gamma",
    ),
    (
        "wrapped list continuation preserved",
        "- This is a very long list item copied from a narrow terminal window\nthat should remain part of the same bullet item after cleanup.",
        "- This is a very long list item copied from a narrow terminal window that should remain part of the same bullet item after cleanup.",
    ),
    (
        "numbered list continuation preserved",
        "1. First item has a wrapped continuation line that should stay attached\nand not become a separate paragraph.\n2. second item",
        "1. First item has a wrapped continuation line that should stay attached and not become a separate paragraph.\n2. second item",
    ),
    (
        "hyphen wrap",
        "pre-transac-\ntion checks matter",
        "pre-transaction checks matter",
    ),
    (
        "paragraph break kept",
        "First paragraph line one\nline two\n\nSecond paragraph line one\nline two",
        "First paragraph line one line two\n\nSecond paragraph line one line two",
    ),
    (
        "code fence preserved",
        "```python\nprint('a')\nprint('b')\n```\nwrapped\nline",
        "```python\nprint('a')\nprint('b')\n```\nwrapped line",
    ),
    (
        "table preserved",
        "A | B\n1 | 2\n3 | 4",
        "A | B\n1 | 2\n3 | 4",
    ),
    (
        "colon heading preserved",
        "Summary:\nthis line\nwraps",
        "Summary:\nthis line wraps",
    ),
    (
        "sentence boundary respected",
        "This line ends a sentence.\nNext starts Uppercase",
        "This line ends a sentence.\nNext starts Uppercase",
    ),
    (
        "hard wrap width inference",
        "NorthRiver Labs signed a customer agreement on January\n1, 2026 with a total stated contract value of $900,000.\nThe contract includes three parts and each line was wrapped\nby viewport width rather than intentional paragraph breaks.",
        "NorthRiver Labs signed a customer agreement on January 1, 2026 with a total stated contract value of $900,000. The contract includes three parts and each line was wrapped by viewport width rather than intentional paragraph breaks.",
    ),
    (
        "space-gap wrapped blob recovery",
        "- This is a very long list item copied from a narrow terminal               window and this continuation should stay part of the same bullet item       after fxclip runs.                                                          - second bullet should remain separate.",
        "- This is a very long list item copied from a narrow terminal window and this continuation should stay part of the same bullet item after fxclip runs.\n- second bullet should remain separate.",
    ),
    (
        "unbalanced code fence does not swallow rest",
        "```python\nprint('a')\nFollowing prose should remain prose",
        "```python\nprint('a')\nFollowing prose should remain prose",
    ),
    (
        "inline code-prose split",
        "def score(wallet): return wallet[\"age_days\"] * 2 This wrapped paragraph after code block should reflow.",
        "def score(wallet): return wallet[\"age_days\"] * 2\nThis wrapped paragraph after code block should reflow.",
    ),
    (
        "sentence spacing repaired",
        "This sentence ends.Here is the next sentence",
        "This sentence ends. Here is the next sentence",
    ),
    (
        "paragraph spacing before heading/list",
        "This paragraph is prose.\nSummary:\nline under summary\n- bullet item",
        "This paragraph is prose.\n\nSummary:\nline under summary\n\n- bullet item",
    ),
    (
        "inline bullets separated",
        "This paragraph stays prose. - first bullet item. - second bullet item.",
        "This paragraph stays prose.\n\n- first bullet item.\n- second bullet item.",
    ),
    (
        "list tail prose split",
        "- second bullet should remain separate. pre-transaction wallet trust scoring should reconstruct into one word.",
        "- second bullet should remain separate.\npre-transaction wallet trust scoring should reconstruct into one word.",
    ),
]


def main() -> int:
    failures = 0
    for name, src, expected in CASES:
        out, _ = normalize_text(src)
        if out != expected:
            failures += 1
            print(f"FAIL: {name}")
            print("--- got ---")
            print(out)
            print("--- expected ---")
            print(expected)
    if failures:
        print(f"{failures} test(s) failed")
        return 1
    print(f"OK: {len(CASES)} tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
