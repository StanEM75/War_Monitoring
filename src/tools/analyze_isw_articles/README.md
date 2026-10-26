# Analyze ISW articles

AI semantic deduplication using the OpenAI Responses API. Requires `OPENAI_API_KEY` in the environment and an explicitly chosen model supporting structured outputs. Uses the project's existing `requests` dependency.

From the repository root:

```bash
uv run python src/tools/analyze_isw_articles/deduplicate.py --model YOUR_MODEL_ID
```

Input: `data/outputs/understanding_war_articles/isw_articles.json`.
Default output: `data/outputs/understanding_war_articles/sw_articles_deduplicated.json` in the repository, even when `--input` points elsewhere. The original is preserved.
Cache: `analyze_isw_articles/comparison_cache.json` beside the input.

The first article is retained. Each subsequent full article is compared against retained representatives in input order. Only a `redundant` decision at confidence >= 0.95 excludes an article. New dates, events, numbers, corrections, attribution, or analysis are updates and retained. Uncertain judgments are retained. The report includes excluded URLs, representative URLs, explanations, all comparisons and model metadata. Retained articles keep their original fields, including sources. The raw input preserves all provenance for excluded articles.

`--threshold`, `--max-calls`, `--input`, `--output`, and `--cache` are configurable. The default budget is 100 new comparisons per invocation. Up to N*(N-1)/2 comparisons may be required; no text is silently truncated. Every valid decision is cached, allowing reruns to resume without paying again for unchanged comparisons. If the budget or API fails, no new final report is published; an existing report may therefore be older than the cache. No live API calls are made by tests.

Confidence is the model's self-assessment, not a calibrated probability. Review exclusions before downstream use. Whole articles are grouped; repeated paragraphs inside otherwise informative articles are not removed. Do not run concurrent writers against the same cache/output.

API reference: https://developers.openai.com/api/docs/guides/structured-outputs

## Organize information

After deduplication:

```bash
uv run python src/tools/analyze_isw_articles/organize_information.py
```

Reads `data/outputs/understanding_war_articles/sw_articles_deduplicated.json` and writes `sw_articles_organized.json` in the same directory. Input is preserved. No AI call or API key is required for grouping.

The JSON contains `paragraphs`, each with `title`, combined `text`, and original article metadata. Titles ending in an English date such as `Russian Offensive Campaign Assessment, October 2, 2026` are grouped under `Russian Offensive Campaign Assessment`. Each full text is immediately followed by its date, in chronological order. Whitespace is normalized to form a single paragraph. Undated titles remain unchanged; their texts receive no invented date. Invalid calendar dates are rejected. Source lists in per-article provenance remain limited to three. Use `--input` and `--output` to choose different files.

## Synthetize events

```bash
uv run python src/tools/analyze_isw_articles/synthetize_events.py --model YOUR_MODEL_ID
```

Reads `sw_articles_organized.json` and writes `sw_events_synthesized.json` in `data/outputs/understanding_war_articles/`. Requires `OPENAI_API_KEY`. Makes one structured AI request per title, using the full paragraph, and caches validated results in `analyze_isw_articles/events_cache.json` beside the output. Input remains unchanged. `--input`, `--output`, and `--cache` are configurable.

Each title contains its reporting period and major events with start/end dates, summaries, exact supporting excerpts, and a `formatted` line such as `October 1, 2026 - October 3, 2026: An assault was reported, followed by territorial losses.` Dates are validated against the article metadata and excerpts against the input text. Undatable events are labeled `Undated`. Merely successive facts must not be rewritten as causal claims. Dates represent reporting dates; actual event dates may differ. This AI tool is probabilistic and requires review; mechanical validation does not verify that every claim follows from its quotes. Entire paragraphs are sent without truncation; API context errors stop publication and earlier cached titles allow resuming. An existing output may be stale after a failed run. No concurrent writers against the same artifacts.
