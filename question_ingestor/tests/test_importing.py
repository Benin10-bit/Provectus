import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from question_ingestor.batch.database import open_global
from question_ingestor.importing.postgres import (
    plan, _open_staging, _selected_rows, _validate_question, _verify_asset,
)


class ImportSelectionTests(unittest.TestCase):
    def make_staging(self, root):
        db = open_global(root / 'staging.db')
        with db:
            for sha, state in [('d1', 'DONE'), ('d2', 'FAILED')]:
                db.execute('''INSERT INTO documents
                    (sha256,source_file,pages,metadata_json,processing_status,content_path,materia)
                    VALUES (?,?,?,?,?,?,?)''',
                    (sha, sha + '.pdf', 1, '{}', state, '["Assunto"]', 'Física'))
            db.execute("INSERT INTO processing_jobs(id,document_sha256,config_hash,state) VALUES ('job','d1','config','DONE')")
            for qid, doc, status in [('a','d1','OK'),('b','d1','REVIEW'),
                                      ('c','d1','ERROR'),('d','d2','OK')]:
                q = dict(extraction_id=qid, document_sha256=doc, status=status,
                         enunciado='texto' * 250_000, pagina_inicio=1, pagina_fim=1,
                         gabarito='A', alternativas=[dict(letra='A', texto='opção', imagens=[])],
                         imagens=[], originals=[])
                db.execute('''INSERT INTO questions VALUES(?,?,?,?,?,?,?,?,?,?)''',
                           (qid, doc, 'job', 1, status, 1, 1, None, None,
                            json.dumps(q, ensure_ascii=False)))
        db.close()

    def test_only_ok_from_done_documents_and_no_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_staging(root)
            before = (root / 'staging.db').stat().st_size
            result = plan(root)
            self.assertEqual(result['questions_ok_selected'], 1)
            self.assertEqual(result['documents_selected'], 1)
            self.assertFalse(result['database_modified'])
            db = _open_staging(root)
            try:
                rows = list(_selected_rows(db))
            finally:
                db.close()
            self.assertEqual([q['extraction_id'] for _, q in rows], ['a'])
            self.assertEqual(len(rows[0][1]['enunciado']), 1_250_000)
            _validate_question(rows[0][1])
            self.assertEqual((root / 'staging.db').stat().st_size, before)

    def test_limit_and_document_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_staging(root)
            self.assertEqual(plan(root, limit=1)['questions_ok_selected'], 1)
            self.assertEqual(plan(root, document='d2')['questions_ok_selected'], 0)
            with self.assertRaises(ValueError):
                plan(root, limit=0)

    def test_rejects_inconsistent_answer(self):
        q = {'enunciado': 'Texto', 'alternativas': [{'letra': 'A'}],
             'gabarito': 'B', 'pagina_inicio': 1, 'pagina_fim': 1}
        with self.assertRaisesRegex(ValueError, 'INVALID_OK_ANSWER'):
            _validate_question(q)

    def test_asset_verification_accepts_same_hash_at_two_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            a = root / 'storage/questions/a.webp'
            b = root / 'storage/originals/b.webp'
            a.parent.mkdir(parents=True)
            b.parent.mkdir(parents=True)
            a.write_bytes(b'picture')
            b.write_bytes(b'picture')
            digest = hashlib.sha256(b'picture').hexdigest()
            verified = set()
            for path in ('storage/questions/a.webp', 'storage/originals/b.webp'):
                _verify_asset(root, {'path': path, 'hash': digest, 'size_bytes': 7}, verified)
            self.assertEqual(len(verified), 2)
            b.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'ASSET_INTEGRITY_FAILURE'):
                _verify_asset(root, {'path': 'storage/originals/b.webp',
                                     'hash': digest, 'size_bytes': 7}, set())


if __name__ == '__main__':
    unittest.main()
