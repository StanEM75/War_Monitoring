import importlib.util
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

spec = importlib.util.spec_from_file_location("isw_ingestion", Path(__file__).resolve().parents[1] / "src/ingestion/get_understandwar_data.py")
isw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(isw)


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.pause = Mock()
        original = isw.ingest_articles
        patcher = patch.object(isw, "ingest_articles", side_effect=lambda *args, **kwargs: original(*args, **{ "sleep": self.pause, **kwargs}))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_rate_limit_respects_retry_after_and_recovers(self):
        with tempfile.TemporaryDirectory() as folder:
            session = Mock()
            limited = Mock(status_code=429, headers={"Retry-After": "120"})
            success = Mock(status_code=200, url="https://example.com/a/", text="<article><p>Body</p></article>")
            session.get.side_effect = [limited, success]
            result = isw.ingest_articles(["https://example.com/a"], Path(folder) / "out.json", session)
            self.assertEqual(len(result["articles"]), 1)
            self.assertEqual([call.args[0] for call in self.pause.call_args_list], [120, 5])

    def test_persistent_rate_limit_stops_before_next_url(self):
        with tempfile.TemporaryDirectory() as folder:
            session = Mock()
            session.get.return_value = Mock(status_code=429, headers={})
            result = isw.ingest_articles(["https://example.com/a", "https://example.com/b"], Path(folder) / "out.json", session, max_retries=1)
            self.assertEqual(session.get.call_count, 2)
            self.assertEqual(len(result["errors"]), 1)
            self.assertEqual(self.pause.call_args_list[0].args, (60,))

    def test_http_date_retry_after(self):
        self.assertEqual(isw.retry_after_seconds("invalid"), 0)
        self.assertGreater(isw.retry_after_seconds("Wed, 01 Jan 2100 00:00:00 GMT"), 0)

    def test_candidates_have_valid_dates_and_skip_future(self):
        urls = list(isw.retrieve_understanding_war_links(today=date(2026, 10, 4)))
        self.assertIn(isw.BASE_URL + "/middle-east/iran-update-october-2-2026/", urls)
        self.assertFalse(any("september-31" in url or "october-5-" in url or "november" in url for url in urls))

    def test_skip_success_retry_error_and_deduplicate(self):
        old = isw.BASE_URL + "/middle-east/iran-update-october-01-2026"
        new = isw.BASE_URL + "/middle-east/iran-update-october-2-2026/"
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "articles.json"
            output.write_text(json.dumps({"articles": [{"url": old, "text": "Preserved"}],
                                          "errors": [{"url": new, "error": "Previous failure"}]}))
            session = Mock()
            session.get.return_value.url = new
            session.get.return_value.text = '<article><h1>Title</h1><p>Article body</p><a href="/one">1</a><a href="/one">duplicate</a><a href="/two">2</a><a href="/three">3</a><a href="/four">4</a></article>' 
            result = isw.ingest_articles([isw.normalize_url(old), new, new.rstrip('/')], output, session)
            session.get.assert_called_once_with(new, timeout=30)
            self.assertEqual(len(result['articles']), 2)
            self.assertEqual(result['errors'], [])
            self.assertEqual(result['articles'][1]['sources'], ['https://understandingwar.org/one', 'https://understandingwar.org/two', 'https://understandingwar.org/three'])
            self.assertEqual(json.loads(output.read_text()), result)
            session.reset_mock()
            isw.ingest_articles([old, new], output, session)
            session.get.assert_not_called()

    def test_failures_remain_retryable_and_do_not_block_next_article(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'articles.json'
            session = Mock()
            response = Mock(url="https://example.com/valid/", text='<article><p>Body</p></article>')
            session.get.side_effect = [requests.HTTPError('404'), response]
            result = isw.ingest_articles(['https://example.com/missing', 'https://example.com/valid'], output, session)
            self.assertEqual(len(result['articles']), 1)
            self.assertEqual(len(result['errors']), 1)
            self.pause.assert_called_once_with(5)

    def test_corrupt_storage_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'articles.json'
            output.write_text('invalid JSON')
            with self.assertRaises(json.JSONDecodeError):
                isw.ingest_articles([], output, Mock())
            self.assertEqual(output.read_text(), 'invalid JSON')
