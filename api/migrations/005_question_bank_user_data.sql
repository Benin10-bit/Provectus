-- User-owned organization and progress, separate from the importer tables.
CREATE TABLE question_bank.folders (
 id UUID PRIMARY KEY, parent_id UUID REFERENCES question_bank.folders(id) ON DELETE RESTRICT,
 name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 120), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CONSTRAINT folder_not_self CHECK (parent_id IS NULL OR parent_id <> id)
);
CREATE INDEX qb_folders_parent_idx ON question_bank.folders(parent_id);
CREATE TABLE question_bank.lists (
 id UUID PRIMARY KEY, folder_id UUID REFERENCES question_bank.folders(id) ON DELETE RESTRICT,
 name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 160), created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX qb_lists_folder_idx ON question_bank.lists(folder_id);
CREATE TABLE question_bank.list_questions (
 list_id UUID NOT NULL REFERENCES question_bank.lists(id) ON DELETE CASCADE,
 question_id TEXT NOT NULL REFERENCES question_bank.questions(id) ON DELETE RESTRICT,
 ordinal INTEGER NOT NULL CHECK (ordinal > 0), PRIMARY KEY(list_id,question_id), UNIQUE(list_id,ordinal)
);
CREATE INDEX qb_list_questions_q_idx ON question_bank.list_questions(question_id);
CREATE TABLE question_bank.answers (
 list_id UUID NOT NULL, question_id TEXT NOT NULL,
 letter TEXT NOT NULL, correct BOOLEAN, eliminated JSONB NOT NULL DEFAULT '[]'::jsonb,
 answered_at TIMESTAMPTZ,
 PRIMARY KEY(list_id,question_id),
 FOREIGN KEY(list_id,question_id) REFERENCES question_bank.list_questions(list_id,question_id) ON DELETE CASCADE
);
CREATE INDEX qb_questions_bank_difficulty_idx ON question_bank.questions(banca_normalizada,dificuldade_normalizada);
CREATE INDEX qb_documents_content_path_idx ON question_bank.documents USING GIN(content_path);
