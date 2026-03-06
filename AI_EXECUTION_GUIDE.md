# PSiteDL AI Execution Guide

This document is for AI agents/tools to execute PSiteDL batch download reliably.

## 1) Command to run

Use this script as the single entrypoint:

```bash
/Users/yr001/Documents/New\ project/PSiteDL/run_psitedl_batch.sh <URL_FILE> [OUTPUT_DIR]
```

- `<URL_FILE>`: required, absolute path to a text file containing URLs.
- `[OUTPUT_DIR]`: optional, absolute output directory. Default: `~/Downloads`.

## 2) URL file format

- One URL per line.
- Empty lines are allowed.
- Lines starting with `#` are ignored as comments.

Example:

```text
# batch task
https://example.com/video1
https://example.com/video2
```

## 3) Agent input contract

Required inputs:
- `url_file_abs_path`

Optional inputs:
- `output_dir_abs_path` (if missing, use `/Users/yr001/Downloads`)

Pre-checks:
- Verify `url_file_abs_path` exists and is readable.
- Ensure path is absolute.

## 4) Agent execution template

```bash
/Users/yr001/Documents/New\ project/PSiteDL/run_psitedl_batch.sh \
  "<url_file_abs_path>" \
  "<output_dir_abs_path>"
```

If output dir not provided:

```bash
/Users/yr001/Documents/New\ project/PSiteDL/run_psitedl_batch.sh \
  "<url_file_abs_path>"
```

## 5) Expected runtime behavior

The script will:
1. Create/reuse venv at `PSiteDL/.venv`
2. Install/update dependencies (`pip`, project editable install, `yt-dlp`, `playwright`)
3. Run:
   - `psitedl --url-file <URL_FILE> --output-dir <OUTPUT_DIR>`

## 6) Return code handling

- `0`: overall success (all URLs downloaded)
- `1`: input/usage error (missing file path, file not found)
- `2`: runtime/dependency setup error
- non-zero from `psitedl`: at least one task failed

## 7) Parseable stdout markers (from psitedl)

The agent should parse these lines:
- `[task] i/n <url>`
- `[log] <abs_log_path>`
- `[saved] <abs_file_path>`
- `[error] ...`
- `[summary] total=X success=Y failed=Z`

Success rule:
- Prefer `[summary] ... failed=0`
- If no summary, require exit code `0` and at least one `[saved]`

## 8) Failure workflow for AI agent

When command fails:
1. Capture exit code and full stdout/stderr.
2. Extract latest `[log]` path.
3. Read that log file and report:
   - `[fatal]`
   - `[selected-url]`
   - `[download-exit]`
4. Return concise diagnosis and next action.

## 9) Common remediation hints

- `未找到 yt-dlp`:
  - script should auto-install; if still failing, check Python/pip permissions.
- `playwright 不可用`:
  - run: `python -m pip install playwright`
- `urlopen error ... nodename nor servname provided`:
  - DNS/network issue in execution environment, not URL-file parsing logic.

