-- Existing lists stay unchanged. Only newly composed lists receive metadata.
ALTER TABLE question_bank.lists ADD COLUMN generation JSONB;
