-- Additive only. Existing cycle, records, credentials and volumes remain untouched.
CREATE TABLE tb_config_metas (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    dados JSON NOT NULL,
    criada_em TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);
CREATE TABLE tb_semana_metas (
    inicio DATE PRIMARY KEY,
    plano JSON NOT NULL,
    criada_em TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);
INSERT INTO tb_config_metas (id, dados) VALUES (1, '{"dias":[
 {"dia":0,"inicio":"14:45","fim":"19:00","pausas":45,"minutos":180},
 {"dia":1,"inicio":"15:15","fim":"19:00","pausas":45,"minutos":150},
 {"dia":2,"inicio":"15:25","fim":"19:00","pausas":40,"minutos":150},
 {"dia":3,"inicio":"20:00","fim":"21:00","pausas":10,"minutos":45},
 {"dia":4,"inicio":"21:00","fim":"22:00","pausas":10,"minutos":45},
 {"dia":5,"inicio":"07:30","fim":"15:00","pausas":120,"minutos":270},
 {"dia":6,"inicio":null,"fim":null,"pausas":0,"minutos":0}],
 "percentual_pratica":40,"minutos_por_questao":6,"redacoes":1}');
