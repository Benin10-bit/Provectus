-- Durable practice history, independent from lists and PROVECTUS performance.
CREATE TABLE question_bank.solved_questions (
 question_id TEXT PRIMARY KEY REFERENCES question_bank.questions(id) ON DELETE CASCADE,
 answered_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Recover all existing completed list answers. Cuts alone are not attempts.
INSERT INTO question_bank.solved_questions(question_id,answered_at)
 SELECT question_id,min(answered_at) FROM question_bank.answers
 WHERE answered_at IS NOT NULL GROUP BY question_id
 ON CONFLICT(question_id) DO NOTHING;
