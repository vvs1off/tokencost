# tokencost

Offline token-count and LLM **cost estimation** for a string, a file, stdin, or
a whole repository. Zero dependencies, standard library only, Python 3.10+.

```
$ tokencost README.md -m medium
tokencost — 1 file(s)
method: heuristic   currency: USD
input tokens:  1,284
output tokens: 0

MODEL          INPUT        OUTPUT         TOTAL
medium      0.003852      0.000000      0.003852

note: prices are UNVERIFIED placeholders — override with --pricing and verify against the provider.
note: token counts are heuristic estimates, not an exact tokenizer.
```

> **Read this first.** Two numbers in this tool are *estimates*, by design:
>
> 1. **Token counts are heuristic.** tokencost does not bundle a vendor
>    tokenizer, so it approximates how BPE tokenizers split text. Good enough for
>    budgeting and comparison; not a substitute for the provider's own tokenizer
>    when you need exact billing.
> 2. **Shipped prices are placeholders.** They are round, illustrative numbers
>    marked `verified: false`, not quoted rates. Provider pricing changes often —
>    override the table with current numbers (`--pricing`) before trusting a cost.
>
> The value of this tool is the mechanism (count → cost), not the shipped figures.

## Install

```bash
# from a clone
git clone https://github.com/vvs1off/tokencost
cd tokencost
pip install .

# or run without installing (zero deps)
python -m tokencost --help
```

## Usage

```bash
# a literal string
tokencost --text "hello world"

# a file, priced for one model
tokencost README.md -m medium

# stdin ('-' explicitly, or just pipe — it is the default when piped)
git diff | tokencost -

# a whole directory (respects .gitignore), Python files only, JSON out
tokencost ./src --include '*.py' --json

# add assumed completion tokens so the output price is included
tokencost prompt.txt -m medium --output-tokens 500

# per-file breakdown
tokencost ./ --by-file
```

If no `-m/--model` is given, every model in the active table is priced.

### Options

| Flag | Meaning |
|------|---------|
| `SOURCE ...` | files or directories; `-` reads stdin (default when piped) |
| `--text STR` | measure a literal string |
| `-m, --model NAME` | price this model (repeatable); default: all models |
| `--method {heuristic,chars}` | estimation method (default `heuristic`) |
| `--chars-per-token N` | divisor for `--method chars` (default `4.0`) |
| `--pricing FILE` | JSON price table merged over the defaults |
| `--output-tokens N` | assumed completion tokens, priced at the output rate |
| `--include GLOB` / `--exclude GLOB` | filter files in repo mode (repeatable) |
| `--no-gitignore` | do not honour `.gitignore` when scanning |
| `--by-file` | per-file token breakdown |
| `--json` | stable JSON output |
| `--list-models` | list models in the active table |
| `-v, --verbose` / `--version` | detail / version |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | success |
| `1` | runtime error (missing file, bad pricing table, unknown model) |
| `2` | usage error (bad arguments) |

## Token estimation

Two offline, deterministic methods:

- **`heuristic`** (default) splits text into runs of letters, digits, whitespace
  and punctuation, then sizes each run the way BPE merges tend to: ~4 characters
  per token for words, more fragmentation for digit runs, punctuation roughly one
  token each, newlines one token, spaces absorbed.
- **`chars`** is the flat "~4 characters per token" rule: `len(text) / divisor`.

Neither reproduces a specific provider's tokenizer exactly. On ordinary English
prose and source code the heuristic is usually in the right ballpark, but the
error grows on unusual input (long base64/hex blobs, dense punctuation, non-Latin
scripts). **Accuracy against any given vendor tokenizer is not independently
validated in this repo** — if you need exact counts, run the provider's
tokenizer and feed the numbers in, or price from `--output-tokens` and a known
input count.

## Pricing

Prices are USD per **1,000,000 tokens**, split into input (prompt) and output
(completion) rates. The shipped defaults are placeholders:

| model | input / 1M | output / 1M | verified |
|-------|-----------:|------------:|:--------:|
| small | 0.50 | 1.50 | false |
| medium | 3.00 | 15.00 | false |
| large | 15.00 | 75.00 | false |

Override with your own table. Pass `--pricing FILE` or set `TOKENCOST_PRICING`:

```json
{
  "currency": "USD",
  "per_tokens": 1000000,
  "models": {
    "my-provider-model": {"input": 3.0, "output": 15.0, "verified": true}
  }
}
```

A user table is **merged over** the defaults: listed models are replaced or
added, unlisted defaults are kept. Set `"verified": true` on entries you have
checked against the provider — the report and the `prices_verified` JSON field
reflect it.

## JSON schema

`--json` emits a stable object:

```json
{
  "tokencost_version": "0.1.0",
  "method": "heuristic",
  "currency": "USD",
  "per_tokens": 1000000,
  "input_tokens": 1284,
  "output_tokens": 0,
  "file_count": 1,
  "prices_verified": false,
  "models": [
    {"model": "medium", "input_cost": 0.003852, "output_cost": 0.0, "total_cost": 0.003852, "verified": false}
  ],
  "files": [{"path": "README.md", "tokens": 1284}]
}
```

`files` is present when files or directories were scanned.

## Privacy

Fully offline. No network access, no telemetry. Your text and files never leave
your machine.

## Demo

![demo](assets/demo.gif)

<!-- assets/demo.gif is a placeholder; record a terminal demo before release. -->

## Development

```bash
pip install -e ".[dev]"
python -m pytest -q
```

CI runs the suite on Python 3.10–3.13 (see `.github/workflows/ci.yml`).

## License

MIT — see [LICENSE](LICENSE).
