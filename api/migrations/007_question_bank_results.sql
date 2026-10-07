-- Latest known correction, independent from list lifetime and study metrics.
ALTER TABLE question_bank.solved_questions ADD COLUMN correct BOOLEAN;
ALTER TABLE question_bank.solved_questions ADD COLUMN last_answered_at TIMESTAMPTZ;
-- Restore the latest available completed correction from existing lists.
UPDATE question_bank.solved_questions s
 SET correct=latest.correct,last_answered_at=latest.answered_at
 FROM (
   SELECT DISTINCT ON (question_id) question_id,correct,answered_at
   FROM question_bank.answers WHERE answered_at IS NOT NULL AND correct IS NOT NULL
   ORDER BY question_id,answered_at DESC,list_id DESC
 ) latest
 WHERE s.question_id=latest.question_id;
