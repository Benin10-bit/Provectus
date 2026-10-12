-- Nullable measures and explicit provenance. No UPDATE/backfill of existing rows.
ALTER TABLE tb_bloco_questoes ALTER COLUMN dificuldade DROP NOT NULL;
ALTER TABLE tb_bloco_questoes ALTER COLUMN tempo_total_segundos DROP NOT NULL;
ALTER TABLE tb_bloco_questoes ADD COLUMN dificuldade_informada BOOLEAN;
ALTER TABLE tb_bloco_questoes ADD COLUMN tempo_questoes_informado BOOLEAN;
-- NOT VALID preserves legacy data; new and edited rows respect the contract.
ALTER TABLE tb_bloco_questoes ADD CONSTRAINT ck_bloco_medidas_opcionais CHECK (
    (dificuldade IS NULL OR dificuldade BETWEEN 1 AND 5)
    AND (tempo_total_segundos IS NULL OR tempo_total_segundos > 0)
    AND (dificuldade_informada IS NOT TRUE OR dificuldade IS NOT NULL)
    AND (tempo_questoes_informado IS NOT TRUE OR tempo_total_segundos IS NOT NULL)
) NOT VALID;
