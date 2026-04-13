# fxclip

Deterministic clipboard text normalizer for terminal-wrap artifacts.

## What It Does
- Repairs accidental soft wraps from terminal copy.
- Preserves intentional structure (headings, lists, tables, fenced code).
- Reduces redundant spacing outside code blocks.
- Splits collapsed inline markers (list/heading/table/code) into readable blocks.

## Files
- `fxclip_core.py`: core normalization engine.
- `fxclip_tests.py`: regression tests.
- `fxclip-watch.ps1`: optional Windows clipboard watcher.
- `fxclip-watch.cmd`: optional Startup launcher.
- `check.sh`: quick integrity check.

## Quick Start
### Manual use
```bash
python3 fxclip_core.py < input.txt > output.txt
```

### Run tests
```bash
bash check.sh
```

## Optional Auto-Watch (Windows)
1. Copy `fxclip-watch.ps1` to `%USERPROFILE%\fxclip-watch.ps1`.
2. Optionally set the core path:
```powershell
setx FXCLIP_CORE "/path/to/fxclip_core.py"
```
3. Start watcher:
```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\fxclip-watch.ps1"
```
4. Optional startup: place `fxclip-watch.cmd` in Startup folder.

## Security / Publishing Notes
- Do not commit personal documents from adjacent directories.
- Do not commit local logs (`fxclip-watch.log`).
- Keep repository scoped to this `fxclip/` folder.

## Limitations
If copied content loses all true newlines and only preserves large space runs,
reconstruction is best-effort and may remain partially ambiguous.
