-- Original schema; applied only to a database with no Provectus tables.
CREATE TYPE statusredacao AS ENUM ('critica', 'fraca', 'regular', 'boa', 'muito_boa', 'excelente');

CREATE TABLE tb_materia (
	id UUID NOT NULL, 
	nome VARCHAR(50) NOT NULL, 
	peso_prova NUMERIC(5, 2) NOT NULL, 
	ativa BOOLEAN, 
	criado_em TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (nome)
);

CREATE TABLE tb_simulado_semanal (
	id UUID NOT NULL, 
	numero_ciclo INTEGER NOT NULL, 
	numero_semana INTEGER NOT NULL, 
	total_questoes INTEGER NOT NULL, 
	total_acertos INTEGER NOT NULL, 
	tempo_total_segundos INTEGER NOT NULL, 
	nivel_ansiedade INTEGER, 
	nivel_fadiga INTEGER, 
	qualidade_sono INTEGER, 
	criado_em TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE tb_prova_oficial (
	id UUID NOT NULL, 
	ano INTEGER NOT NULL, 
	nota_total NUMERIC(5, 2) NOT NULL, 
	tempo_total_segundos INTEGER NOT NULL, 
	nivel_ansiedade INTEGER, 
	nivel_fadiga INTEGER, 
	qualidade_sono INTEGER, 
	criado_em TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE tb_redacoes (
	id UUID NOT NULL, 
	tema TEXT NOT NULL, 
	eixo_tematico VARCHAR(100) NOT NULL, 
	data_escrita TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	tempo_escrita_min INTEGER, 
	observacoes TEXT, 
	repertorios TEXT, 
	criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE tb_assunto (
	id UUID NOT NULL, 
	materia_id UUID NOT NULL, 
	nome VARCHAR(120) NOT NULL, 
	semana_do_ciclo INTEGER NOT NULL, 
	ativo BOOLEAN, 
	criado_em TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(materia_id) REFERENCES tb_materia (id)
);

CREATE TABLE tb_desempenho_simulado_materia (
	id UUID NOT NULL, 
	simulado_id UUID NOT NULL, 
	materia_id UUID NOT NULL, 
	total_questoes INTEGER NOT NULL, 
	total_acertos INTEGER NOT NULL, 
	tempo_total_segundos INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(simulado_id) REFERENCES tb_simulado_semanal (id), 
	FOREIGN KEY(materia_id) REFERENCES tb_materia (id)
);

CREATE TABLE tb_desempenho_prova_materia (
	id UUID NOT NULL, 
	prova_id UUID NOT NULL, 
	materia_id UUID NOT NULL, 
	percentual_acerto NUMERIC(5, 2) NOT NULL, 
	tempo_total_segundos INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(prova_id) REFERENCES tb_prova_oficial (id), 
	FOREIGN KEY(materia_id) REFERENCES tb_materia (id)
);

CREATE TABLE tb_competencias_redacao (
	id UUID NOT NULL, 
	redacao_id UUID NOT NULL, 
	competencia INTEGER NOT NULL, 
	nota INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT check_competencia_range CHECK (competencia BETWEEN 1 AND 5), 
	CONSTRAINT check_nota_range CHECK (nota BETWEEN 0 AND 200), 
	FOREIGN KEY(redacao_id) REFERENCES tb_redacoes (id) ON DELETE CASCADE
);

CREATE TABLE tb_analises_redacao (
	id UUID NOT NULL, 
	redacao_id UUID NOT NULL, 
	nota_total INTEGER NOT NULL, 
	status statusredacao NOT NULL, 
	competencia_mais_fraca INTEGER NOT NULL, 
	diagnostico TEXT, 
	recomendacao TEXT, 
	criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (redacao_id), 
	FOREIGN KEY(redacao_id) REFERENCES tb_redacoes (id) ON DELETE CASCADE
);

CREATE TABLE tb_sessao_estudo (
	id UUID NOT NULL, 
	data TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	materia_id UUID NOT NULL, 
	assunto_id UUID NOT NULL, 
	tipo_sessao VARCHAR(20) NOT NULL, 
	minutos_liquidos INTEGER NOT NULL, 
	nivel_foco INTEGER, 
	nivel_energia INTEGER, 
	criado_em TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(materia_id) REFERENCES tb_materia (id), 
	FOREIGN KEY(assunto_id) REFERENCES tb_assunto (id)
);

CREATE TABLE tb_bloco_questoes (
	id UUID NOT NULL, 
	data TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	materia_id UUID NOT NULL, 
	assunto_id UUID NOT NULL, 
	dificuldade INTEGER NOT NULL, 
	total_questoes INTEGER NOT NULL, 
	total_acertos INTEGER NOT NULL, 
	tempo_total_segundos INTEGER NOT NULL, 
	nivel_confianca_medio INTEGER, 
	criado_em TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(materia_id) REFERENCES tb_materia (id), 
	FOREIGN KEY(assunto_id) REFERENCES tb_assunto (id)
);

CREATE TABLE tb_erro_questao (
	id UUID NOT NULL, 
	bloco_id UUID NOT NULL, 
	tipo_erro VARCHAR(30) NOT NULL, 
	quantidade INTEGER NOT NULL, 
	criado_em TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(bloco_id) REFERENCES tb_bloco_questoes (id)
);
