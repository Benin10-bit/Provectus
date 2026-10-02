CREATE TABLE tb_ciclo (
	id UUID NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	iniciado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	encerrado_em TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE tb_planejamento (
	id SERIAL NOT NULL, 
	ciclo_id UUID, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ciclo_id) REFERENCES tb_ciclo (id)
);

CREATE TABLE tb_meta_ciclo (
	id UUID NOT NULL, 
	ciclo_id UUID NOT NULL, 
	materia_id UUID NOT NULL, 
	minutos INTEGER NOT NULL, 
	ordem INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_meta_ciclo_materia UNIQUE (ciclo_id, materia_id), 
	CONSTRAINT ck_meta_minutos CHECK (minutos > 0), 
	FOREIGN KEY(ciclo_id) REFERENCES tb_ciclo (id), 
	FOREIGN KEY(materia_id) REFERENCES tb_materia (id)
);

CREATE TABLE tb_acao_estudo (
	id UUID NOT NULL, 
	assunto_id UUID NOT NULL, 
	bloco_id UUID, 
	descricao VARCHAR(300) NOT NULL, 
	causa VARCHAR(30), 
	prevista_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	criada_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	concluida_em TIMESTAMP WITHOUT TIME ZONE, 
	resultado VARCHAR(30), 
	PRIMARY KEY (id), 
	FOREIGN KEY(assunto_id) REFERENCES tb_assunto (id), 
	FOREIGN KEY(bloco_id) REFERENCES tb_bloco_questoes (id)
);

INSERT INTO tb_planejamento (id) VALUES (1);
ALTER TABLE tb_assunto ADD COLUMN ordem INTEGER NOT NULL DEFAULT 0;
ALTER TABLE tb_assunto ADD COLUMN referencia VARCHAR(300);
ALTER TABLE tb_sessao_estudo ADD COLUMN ciclo_id UUID REFERENCES tb_ciclo(id);
ALTER TABLE tb_sessao_estudo ADD COLUMN chave_registro UUID UNIQUE;
ALTER TABLE tb_sessao_estudo ADD COLUMN conteudo_hash VARCHAR(64);
ALTER TABLE tb_sessao_estudo ADD COLUMN segundos_exatos INTEGER;
ALTER TABLE tb_sessao_estudo ADD COLUMN atividade VARCHAR(30);
ALTER TABLE tb_sessao_estudo ADD COLUMN proximo_passo VARCHAR(300);
ALTER TABLE tb_bloco_questoes ADD COLUMN sessao_id UUID UNIQUE REFERENCES tb_sessao_estudo(id);
ALTER TABLE tb_bloco_questoes ADD COLUMN ciclo_id UUID REFERENCES tb_ciclo(id);
-- NOT VALID preserves legacy rows; all new writes and changed rows are checked.
ALTER TABLE tb_simulado_semanal ADD CONSTRAINT ck_sim_contagem CHECK (total_questoes > 0 AND total_acertos BETWEEN 0 AND total_questoes AND tempo_total_segundos > 0) NOT VALID;
ALTER TABLE tb_bloco_questoes ADD CONSTRAINT ck_bloco_contagem CHECK (total_questoes > 0 AND total_acertos BETWEEN 0 AND total_questoes AND tempo_total_segundos > 0 AND dificuldade BETWEEN 1 AND 5) NOT VALID;
ALTER TABLE tb_sessao_estudo ADD CONSTRAINT ck_sessao_duracao CHECK (minutos_liquidos > 0 AND (segundos_exatos IS NULL OR segundos_exatos > 0)) NOT VALID;
ALTER TABLE tb_assunto ADD CONSTRAINT uq_assunto_id_materia UNIQUE (id, materia_id);
ALTER TABLE tb_sessao_estudo ADD CONSTRAINT fk_sessao_assunto_materia FOREIGN KEY (assunto_id, materia_id) REFERENCES tb_assunto(id, materia_id) NOT VALID;
ALTER TABLE tb_bloco_questoes ADD CONSTRAINT fk_bloco_assunto_materia FOREIGN KEY (assunto_id, materia_id) REFERENCES tb_assunto(id, materia_id) NOT VALID;
CREATE INDEX ix_sessao_data_materia ON tb_sessao_estudo(data, materia_id);
CREATE INDEX ix_bloco_data_materia ON tb_bloco_questoes(data, materia_id);
CREATE INDEX ix_sessao_assunto ON tb_sessao_estudo(assunto_id, data);
CREATE INDEX ix_bloco_assunto ON tb_bloco_questoes(assunto_id, data);
CREATE INDEX ix_simulado_data ON tb_simulado_semanal(criado_em);
CREATE INDEX ix_erro_bloco ON tb_erro_questao(bloco_id);
CREATE INDEX ix_acao_aberta ON tb_acao_estudo(assunto_id, prevista_em) WHERE concluida_em IS NULL;
CREATE INDEX ix_sessao_ciclo ON tb_sessao_estudo(ciclo_id);
CREATE INDEX ix_bloco_ciclo ON tb_bloco_questoes(ciclo_id);
