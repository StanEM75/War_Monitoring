# Temporary output-language override

All agents, sub-agents, and tools operating within this repository must apply the following rule to every new run.

## English-only outputs

Produce all generated textual output exclusively in English. This requirement applies to:

- Agent and sub-agent messages, progress updates, handoffs, and final responses.
- Human-facing reports, summaries, tables, headings, labels, descriptions, recommendations, reasons, warnings, limitations, and review cards.
- Textual fields generated in JSON, Markdown, HTML, CSV, logs, manifests, caches, state files, audit files, and other tool artifacts.
- Controlled error messages and command-line output produced by repository tools.

Do not generate French or any other language in new output artifacts, even when the user writes in another language or an older instruction requests French output. Preserve source data, quoted source text, filenames, paths, identifiers, code, established schema keys, and third-party output in their original form when translating or altering them would corrupt evidence or machine compatibility.

Existing reports and source repository files do not need to be rewritten. Apply this rule to outputs created after this override is added. This is a temporary repository-level instruction and remains active until the user changes or removes it.
