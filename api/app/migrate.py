"""Ordered, transactional PostgreSQL migrations. Never drops, renames or seeds user data."""
from pathlib import Path
import hashlib
from sqlalchemy import text, inspect
from .database import engine

MIGRATIONS = Path(__file__).resolve().parent.parent / 'migrations'
LEGACY_TABLES = {'tb_materia','tb_assunto','tb_sessao_estudo','tb_bloco_questoes','tb_erro_questao',
    'tb_simulado_semanal','tb_desempenho_simulado_materia','tb_prova_oficial','tb_desempenho_prova_materia',
    'tb_redacoes','tb_competencias_redacao','tb_analises_redacao'}

def migrate(bind=engine):
    if bind.dialect.name != 'postgresql':
        raise RuntimeError('Migrações exigem PostgreSQL. Use apenas um banco de teste para validação.')
    with bind.begin() as conn:
        conn.execute(text('SELECT pg_advisory_xact_lock(72652101)'))
        conn.execute(text('CREATE TABLE IF NOT EXISTS provectus_migrations (version VARCHAR(120) PRIMARY KEY, sha256 VARCHAR(64) NOT NULL, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())'))
        applied=dict(conn.execute(text('SELECT version, sha256 FROM provectus_migrations')).all())
        for file in sorted(MIGRATIONS.glob('*.sql')):
            source=file.read_text();checksum=hashlib.sha256(source.encode()).hexdigest()
            if file.name in applied:
                if applied[file.name]!=checksum:raise RuntimeError(f'Migração já aplicada foi modificada: {file.name}')
                continue
            skip=False
            if file.name.startswith('001_'):
                present=set(inspect(conn).get_table_names()) & LEGACY_TABLES
                if present and present!=LEGACY_TABLES:
                    raise RuntimeError('Estrutura anterior incompleta. Nenhum dado foi alterado; confira a versão do banco antes de migrar.')
                skip=bool(present)
            if not skip:
                # Files contain simple SQL statements, no procedural blocks.
                sql = '\n'.join(line for line in source.splitlines() if not line.lstrip().startswith('--'))
                for statement in sql.split(';'):
                    if statement.strip():conn.exec_driver_sql(statement)
            conn.execute(text('INSERT INTO provectus_migrations (version,sha256) VALUES (:v,:h)'),dict(v=file.name,h=checksum))
            print(f'{file.name}: ' + ('estrutura existente reconhecida' if skip else 'aplicada'))
    print('Migrações concluídas. Registros e identificadores preservados.')

if __name__=='__main__':
    migrate()
