-- Nullable provenance only. No historical backfill, fabricated sessions or metrics.
ALTER TABLE tb_assunto ADD COLUMN IF NOT EXISTS familiaridade_declarada VARCHAR(20);
ALTER TABLE tb_assunto ADD COLUMN IF NOT EXISTS familiaridade_alterada_em TIMESTAMP;
ALTER TABLE tb_assunto ADD CONSTRAINT ck_familiaridade CHECK (familiaridade_declarada IN ('ESTUDADO','NAO_ESTUDADO'));
ALTER TABLE tb_sessao_estudo ADD COLUMN IF NOT EXISTS finalidade VARCHAR(20);
ALTER TABLE tb_sessao_estudo ADD COLUMN IF NOT EXISTS objetivo_revisao VARCHAR(200);
ALTER TABLE tb_sessao_estudo ADD COLUMN IF NOT EXISTS classe_revisao VARCHAR(20);
ALTER TABLE tb_sessao_estudo ADD CONSTRAINT ck_finalidade CHECK (finalidade IN ('AVANCO','CONSOLIDACAO','REVISAO'));
ALTER TABLE tb_sessao_estudo ADD CONSTRAINT ck_classe_revisao CHECK (classe_revisao IN ('MANUTENCAO','RECORRENTE','PRIORITARIA'));
ALTER TABLE tb_acao_estudo ADD COLUMN IF NOT EXISTS consequencia VARCHAR(300);
ALTER TABLE tb_acao_estudo ADD COLUMN IF NOT EXISTS uso_em TIMESTAMP;
