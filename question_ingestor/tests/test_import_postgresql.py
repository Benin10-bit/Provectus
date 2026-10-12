"""Opt-in transaction regression, exclusively in a new disposable test database."""
import os
from unittest.mock import patch
import unittest

from question_ingestor.importing import postgres
from test_import_failures import Staging


@unittest.skipUnless(os.getenv('PROVECTUS_TEST_DATABASE_URL'), 'PostgreSQL descartável não configurado')
class PostgreSQLImportTests(unittest.TestCase):
    def test_partial_document_failure_preserves_real_commits_and_counts(self):
        import psycopg
        dsn = os.environ['PROVECTUS_TEST_DATABASE_URL']
        with psycopg.connect(dsn, autocommit=True) as observer:
            if observer.info.dbname != 'provectus_etapa1_test':
                self.fail('Use exclusivamente o banco descartável provectus_etapa1_test.')
            if observer.execute("SELECT 1 FROM pg_namespace WHERE nspname='question_bank'").fetchone():
                self.fail('O banco de teste precisa estar vazio; nenhum schema existente será alterado.')
            observer.execute('CREATE SCHEMA question_bank')
            try:
                observer.execute('''CREATE TABLE question_bank.import_jobs (
                    id UUID PRIMARY KEY, status TEXT, scope JSONB,
                    imported_count INT DEFAULT 0, skipped_count INT DEFAULT 0,
                    finished_at TIMESTAMPTZ, error_code TEXT)''')
                observer.execute('CREATE TABLE question_bank.questions (id TEXT PRIMARY KEY, import_job_id UUID)')
                primary = ValueError('SECOND_DOCUMENT_FAILURE')
                rows = {'a': [{'id': 'saved'}, {'id': 'existing', 'skipped': True}],
                        'b': [{'id': 'rolled-back'}, {'id': 'bad', 'fail': True}]}

                def insert(conn, row, q, job, *args):
                    if q.get('skipped'):
                        return False
                    conn.execute('INSERT INTO question_bank.questions VALUES (%s,%s)', (q['id'], job))
                    if q.get('fail'):
                        raise primary
                    return True

                with patch.object(postgres, '_open_staging', return_value=Staging()), \
                     patch.object(postgres, '_connect', side_effect=lambda: psycopg.connect(dsn, autocommit=True)), \
                     patch.object(postgres, '_documents', return_value=[{'sha256': 'a'}, {'sha256': 'b'}]), \
                     patch.object(postgres, '_selected_rows', side_effect=lambda db, doc, *args: [({}, q) for q in rows[doc]]), \
                     patch.object(postgres, '_insert_one', side_effect=insert):
                    with self.assertRaises(ValueError) as caught:
                        postgres.import_ok('/unused-test-staging')
                self.assertIs(caught.exception, primary)
                job = observer.execute('SELECT status,imported_count,skipped_count,error_code FROM question_bank.import_jobs').fetchone()
                self.assertEqual(job, ('FAILED', 1, 1, 'ValueError'))
                self.assertEqual(observer.execute('SELECT id FROM question_bank.questions ORDER BY id').fetchall(), [('saved',)])
            finally:
                # Only the schema created above, in the explicitly named empty test DB.
                observer.execute('DROP SCHEMA question_bank CASCADE')


if __name__ == '__main__':
    unittest.main()
