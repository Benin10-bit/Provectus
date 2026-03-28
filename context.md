eu preciso que vc crie um componente com um gráfico em pizza em um card que deve seguir o layout e design do sistema. Vc tem permissão pra mexer APENAS no frontend. Deve seguir a estética padrão do sistema e deve ficar no final do arquivo [text](frontend/src/pages/Index.tsx), antes dos cards de redação, se somente se, existir alguma seleção de materia no dashboard.
A logica principal, é que vc vai fazer fetch pra rota da api que eu vou mandar logo abaixo, para cada cada matéria que a api já tem no fetch do proprio sistema no arquivo api.ts, assim conseguindo montar o gráfico.
Vc deve fazer fetch seguindo o padrão no arquivo [text](frontend/src/lib/api.ts).
Documentação da api:
GET
/api/v1/performance/dashboard
Dashboard Estratégico de Performance

Consolida indicadores estratégicos:

- Horas líquidas
- Total de questões
- Percentual médio
- IPR geral
- Tendência (ASCENDENTE, ESTÁVEL, DECLÍNIO)
- Status da missão
- Assuntos críticos
- Status das metas (horas e questões)
- Recomendação automática

Permite filtro por período e matéria.

Parameters
Name	Description
periodo
string
(query)
	

Intervalo de análise

Default value : semana
pattern: ^(semana|mes|ano|total)$
materia_id
string | (string | null)($uuid)
(query)
	

Filtrar por matéria específica (UUID)
Responses
Code	Description	Links
200	

Successful Response
Media type
Controls Accept header.

{
  "horas_liquidas": 0,
  "total_questoes": 0,
  "percentual_medio": 0,
  "ipr_geral": 0,
  "tendencia": "string",
  "status_missao": "string",
  "assuntos_criticos": [
    "string"
  ],
  "status_horas": "string",
  "status_questoes": "string",
  "recomendacao": [
    "string"
  ]
}

	No links
422	

Validation Error
Media type

{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}

OBS: VC DEVE PEGAR APENAS O IPR DE CADA MATÉRIA E O FETCH DE MATÉRIAS JÁ EXISTE NO API.TS