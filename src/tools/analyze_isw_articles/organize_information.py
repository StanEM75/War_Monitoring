"""Group deduplicated ISW article texts by their undated title."""
import argparse
from datetime import date
import json
from pathlib import Path
import re

if __package__:
    from .deduplicate import save_json
else:
    from deduplicate import save_json

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = ROOT / 'data/outputs/understanding_war_articles/sw_articles_deduplicated.json'
DEFAULT_OUTPUT = DEFAULT_INPUT.with_name('sw_articles_organized.json')
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June',
          'July', 'August', 'September', 'October', 'November', 'December')
DATE_SUFFIX = re.compile(
    r'^(?P<title>.+?)[\s,–—:-]+(?P<month>' + '|'.join(MONTHS)
    + r')\s+(?P<day>\d{1,2}),\s*(?P<year>\d{4})\s*$', re.IGNORECASE)


def split_title(title):
    """Arguments: title, an article title optionally ending in an English date.

    Purpose: Extract the group title and a validated date suffix.
    Output: Tuple of group title, display date, and date object; None dates when absent.
    Used in: organize_information.
    """
    match = DATE_SUFFIX.fullmatch(title.strip())
    if not match:
        return title.strip(), None, None
    month = next(i for i, name in enumerate(MONTHS, 1) if name.lower() == match['month'].lower())
    day, year = int(match['day']), int(match['year'])
    parsed = date(year, month, day)
    return match['title'].strip(), f'{MONTHS[month - 1]} {day}, {year}', parsed


def organize_information(input_path=DEFAULT_INPUT, output_path=DEFAULT_OUTPUT):
    """Arguments: input_path, deduplicated article JSON; output_path, grouped JSON.

    Purpose: Group full texts by undated title and append each article's title date.
    Output: Dictionary containing paragraphs; also writes it as JSON without changing input.
    Used in: main and organization tests.
    """
    input_path, output_path = Path(input_path), Path(output_path)
    if input_path.resolve() == output_path.resolve():
        raise ValueError('Input and output must be different files.')
    payload = json.loads(input_path.read_text(encoding='utf-8'))
    articles = payload['articles']
    if not isinstance(articles, list):
        raise ValueError('articles must be a list.')
    groups = {}
    for index, article in enumerate(articles):
        if not isinstance(article, dict) or any(not isinstance(article.get(key), str) or not article[key].strip() for key in ('title', 'text')):
            raise ValueError(f'Article {index} requires nonempty title and text strings.')
        title, display_date, parsed_date = split_title(article['title'])
        groups.setdefault(title, []).append((parsed_date, index, article, display_date))
    paragraphs = []
    for title, entries in groups.items():
        # Chronological order; undated entries follow dated ones in original order.
        entries.sort(key=lambda item: (item[0] is None, item[0] or date.max, item[1]))
        texts = []
        for _, _, article, display_date in entries:
            text = re.sub(r'\s+', ' ', article['text']).strip()
            texts.append(f'{text} {display_date}' if display_date else text)
        paragraphs.append({'title': title, 'text': ' '.join(texts),
                           'articles': [{'title': a['title'], 'date': d, 'url': a.get('url'),
                                         'sources': list(dict.fromkeys(a.get('sources', [])))[:3]}
                                        for _, _, a, d in entries]})
    result = {'paragraphs': paragraphs}
    save_json(output_path, result)
    return result


def main():
    """Arguments: --input and --output CLI paths, both optional.

    Purpose: Run article grouping from the terminal without an AI call.
    Output: JSON artifact and a terminal summary.
    Used in: Direct script execution.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = organize_information(args.input, args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f'{error}\n')
    print(f"Paragraphs: {len(result['paragraphs'])}; output: {args.output}")


if __name__ == '__main__':
    main()
