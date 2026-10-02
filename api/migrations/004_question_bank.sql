-- Isolated question bank; existing public tables remain unchanged.
CREATE SCHEMA IF NOT EXISTS question_bank;

CREATE TABLE question_bank.import_jobs (
    id UUID PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('PROCESSING','DONE','FAILED','ROLLED_BACK')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    scope JSONB NOT NULL DEFAULT '{}'::jsonb,
    imported_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    error_code TEXT
);

CREATE TABLE question_bank.documents (
    sha256 TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    relative_path TEXT,
    materia TEXT,
    content_path JSONB NOT NULL DEFAULT '[]'::jsonb,
    pages INTEGER NOT NULL,
    metadata JSONB NOT NULL,
    first_import_job_id UUID REFERENCES question_bank.import_jobs(id)
);

CREATE TABLE question_bank.questions (
    id TEXT PRIMARY KEY,
    document_sha256 TEXT NOT NULL REFERENCES question_bank.documents(sha256),
    import_job_id UUID NOT NULL REFERENCES question_bank.import_jobs(id),
    source_payload_sha256 TEXT NOT NULL,
    automatic_status TEXT NOT NULL CHECK (automatic_status = 'OK'),
    numero_original INTEGER,
    banca_original TEXT,
    banca_normalizada TEXT,
    tipo_origem TEXT,
    dificuldade_original TEXT,
    dificuldade_normalizada TEXT,
    enunciado TEXT NOT NULL,
    gabarito TEXT,
    pagina_inicio INTEGER NOT NULL,
    pagina_fim INTEGER NOT NULL,
    payload JSONB NOT NULL
);

CREATE TABLE question_bank.alternatives (
    question_id TEXT NOT NULL REFERENCES question_bank.questions(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    letter TEXT NOT NULL,
    text TEXT,
    payload JSONB NOT NULL,
    PRIMARY KEY (question_id, ordinal)
);

CREATE TABLE question_bank.assets (
    hash TEXT PRIMARY KEY,
    storage_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    size_bytes BIGINT NOT NULL,
    first_import_job_id UUID REFERENCES question_bank.import_jobs(id)
);

CREATE TABLE question_bank.question_assets (
    question_id TEXT NOT NULL REFERENCES question_bank.questions(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    asset_hash TEXT NOT NULL REFERENCES question_bank.assets(hash),
    type TEXT NOT NULL,
    alternative_letter TEXT,
    page INTEGER,
    bbox JSONB,
    metadata JSONB NOT NULL,
    PRIMARY KEY (question_id, ordinal)
);

CREATE INDEX question_bank_questions_document_idx ON question_bank.questions(document_sha256);
CREATE INDEX question_bank_questions_import_job_idx ON question_bank.questions(import_job_id);
CREATE INDEX question_bank_questions_bank_idx ON question_bank.questions(banca_normalizada);
CREATE INDEX question_bank_questions_difficulty_idx ON question_bank.questions(dificuldade_normalizada);
CREATE INDEX question_bank_documents_materia_idx ON question_bank.documents(materia);
