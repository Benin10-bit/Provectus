"""Exercise import transactions without connecting to PostgreSQL or user staging."""
from contextlib import contextmanager, ExitStack, redirect_stdout
from copy import deepcopy
from io import StringIO
import sys
import types
import unittest
from unittest.mock import patch

from question_ingestor.importing import postgres


class Staging:
    def __init__(self):
        self.closed = False
        self.close_error = None

    def execute(self, sql):
        return []  # No manual overrides in this isolated fixture.

    def close(self):
        self.closed = True
        if self.close_error:
            raise self.close_error


class Connection:
    """Transactional state model: failed document/status transactions roll back only themselves."""
    def __init__(self):
        self.jobs = {}
        self.questions = []
        self.closed = False
        self.job_error = self.status_error = self.close_error = None

    @contextmanager
    def transaction(self):
        before = deepcopy((self.jobs, self.questions))
        try:
            yield
        except BaseException:
            self.jobs, self.questions = before
            raise

    def execute(self, sql, args):
        if 'INSERT INTO question_bank.import_jobs' in sql:
            if self.job_error:
                raise self.job_error
            job, status, _ = args
            self.jobs[job] = dict(status=status, imported_count=0, skipped_count=0)
        elif 'SET imported_count' in sql:
            imported, skipped, job = args
            self.jobs[job]['imported_count'] += imported
            self.jobs[job]['skipped_count'] += skipped
        elif "SET status='FAILED'" in sql:
            if self.status_error:
                raise self.status_error
            error_code, job = args
            self.jobs[job].update(status='FAILED', error_code=error_code)
        elif "SET status='DONE'" in sql:
            self.jobs[args[0]]['status'] = 'DONE'
        else:
            raise AssertionError(sql)

    def close(self):
        self.closed = True
        if self.close_error:
            raise self.close_error


class ImportFailureTests(unittest.TestCase):
    def setUp(self):
        self.staging = Staging()
        self.conn = Connection()
        self.primary = ValueError('DOCUMENT_FAILURE')

    def invoke(self, documents=(), rows=None, connect_error=None, schema_error=None, documents_error=None):
        json_module = types.ModuleType('psycopg.types.json')
        json_module.Jsonb = lambda value: value
        rows = rows or {}

        def connect():
            if connect_error:
                raise connect_error
            return self.conn

        def schema(conn):
            if schema_error:
                raise schema_error

        def get_documents(*args):
            if documents_error:
                raise documents_error
            return [{'sha256': name} for name in documents]

        def insert(conn, row, question, *args):
            if question.get('skipped'):
                return False
            conn.questions.append(question['id'])
            if question.get('fail'):
                raise self.primary
            return True

        with ExitStack() as stack:
            stack.enter_context(redirect_stdout(StringIO()))
            stack.enter_context(patch.dict(sys.modules, {'psycopg.types.json': json_module}))
            stack.enter_context(patch.object(postgres, '_open_staging', return_value=self.staging))
            stack.enter_context(patch.object(postgres, '_connect', side_effect=connect))
            stack.enter_context(patch.object(postgres, '_require_schema', side_effect=schema))
            stack.enter_context(patch.object(postgres, '_documents', side_effect=get_documents))
            stack.enter_context(patch.object(postgres, '_selected_rows', side_effect=lambda db, doc, *args: [({}, q) for q in rows[doc]]))
            stack.enter_context(patch.object(postgres, '_insert_one', side_effect=insert))
            return postgres.import_ok('/unused-test-staging')

    def job(self):
        self.assertEqual(len(self.conn.jobs), 1)
        return next(iter(self.conn.jobs.values()))

    def test_connection_failure_before_job_preserves_original(self):
        with self.assertRaises(ValueError) as caught:
            self.invoke(connect_error=self.primary)
        self.assertIs(caught.exception, self.primary)
        self.assertEqual(self.conn.jobs, {})
        self.assertTrue(self.staging.closed)

    def test_schema_failure_before_job_closes_both_resources(self):
        with self.assertRaises(ValueError) as caught:
            self.invoke(schema_error=self.primary)
        self.assertIs(caught.exception, self.primary)
        self.assertEqual(self.conn.jobs, {})
        self.assertTrue(self.staging.closed and self.conn.closed)

    def test_job_creation_failure_does_not_attempt_failed_update(self):
        self.conn.job_error = self.primary
        self.conn.status_error = AssertionError('must not update an uncreated job')
        with self.assertRaises(ValueError) as caught:
            self.invoke()
        self.assertIs(caught.exception, self.primary)
        self.assertEqual(self.conn.jobs, {})

    def test_failure_after_job_marks_failed_with_zero_counts(self):
        with self.assertRaises(ValueError) as caught:
            self.invoke(documents_error=self.primary)
        self.assertIs(caught.exception, self.primary)
        self.assertEqual(self.job(), dict(status='FAILED', imported_count=0, skipped_count=0, error_code='ValueError'))

    def test_committed_document_and_counts_survive_later_document_failure(self):
        rows = {'a': [{'id': 'saved'}, {'id': 'existing', 'skipped': True}],
                'b': [{'id': 'rolled-back'}, {'id': 'bad', 'fail': True}]}
        with self.assertRaises(ValueError) as caught:
            self.invoke(documents=['a', 'b'], rows=rows)
        self.assertIs(caught.exception, self.primary)
        self.assertEqual(self.conn.questions, ['saved'])
        self.assertEqual(self.job(), dict(status='FAILED', imported_count=1, skipped_count=1, error_code='ValueError'))

    def test_failed_status_error_keeps_original_and_committed_counts(self):
        self.conn.status_error = ConnectionError('status unavailable')
        rows = {'a': [{'id': 'saved'}], 'b': [{'id': 'bad', 'fail': True}]}
        with self.assertRaises(ValueError) as caught:
            self.invoke(documents=['a', 'b'], rows=rows)
        self.assertIs(caught.exception, self.primary)
        self.assertEqual(self.conn.questions, ['saved'])
        self.assertEqual(self.job(), dict(status='PROCESSING', imported_count=1, skipped_count=0))
        self.assertIn('import_job_id=', '\n'.join(caught.exception.__notes__))
        self.assertIn('ConnectionError', '\n'.join(caught.exception.__notes__))
        self.assertTrue(self.staging.closed and self.conn.closed)

    def test_cleanup_errors_do_not_replace_import_error(self):
        self.staging.close_error = RuntimeError('staging close failed')
        self.conn.close_error = OSError('connection close failed')
        with self.assertRaises(ValueError) as caught:
            self.invoke(documents_error=self.primary)
        self.assertIs(caught.exception, self.primary)
        self.assertTrue(self.staging.closed and self.conn.closed)
        self.assertEqual(self.job()['status'], 'FAILED')
        self.assertEqual(len(caught.exception.__notes__), 2)

    def test_cleanup_failure_after_success_is_not_silently_ignored(self):
        close_error = OSError('staging close failed')
        self.staging.close_error = close_error
        with self.assertRaises(OSError) as caught:
            self.invoke()
        self.assertIs(caught.exception, close_error)
        self.assertEqual(self.job()['status'], 'DONE')
        self.assertTrue(self.staging.closed and self.conn.closed)

    def test_success_keeps_public_result_and_counts(self):
        result = self.invoke(documents=['a'], rows={'a': [{'id': 'saved'}, {'id': 'existing', 'skipped': True}]})
        self.assertEqual(result['status'], 'DONE')
        self.assertEqual((result['imported'], result['skipped']), (1, 1))
        self.assertEqual(result['job_id'], str(next(iter(self.conn.jobs))))
        self.assertEqual(self.job(), dict(status='DONE', imported_count=1, skipped_count=1))


if __name__ == '__main__':
    unittest.main()
