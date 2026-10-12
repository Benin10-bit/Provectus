"""Monthly report regression via HTTP and the existing disposable ORM fixture."""
from datetime import datetime
from uuid import UUID
import pytest
from sqlalchemy.orm import Session

from test_flows import env, catalog
from app import models, services


@pytest.fixture
def report(env, monkeypatch):
    client, engine = env
    (materia, assunto), _ = catalog(client)
    monkeypatch.setattr(services, 'utcnow', lambda: datetime(2026, 10, 1, 12))

    def read(current, previous, classified_current=(), classified_previous=()):
        with Session(engine) as db:
            for month, rows, classifications in [(9, current, classified_current), (8, previous, classified_previous)]:
                for index, (total, hits) in enumerate(rows):
                    block = models.BlocoQuestoes(materia_id=UUID(materia), assunto_id=UUID(assunto),
                        data=datetime(2026, month, index + 2, 12), total_questoes=total,
                        total_acertos=hits, tempo_total_segundos=600, dificuldade=3)
                    db.add(block)
                    db.flush()
                    if index < len(classifications) and classifications[index]:
                        db.add(models.ErroQuestao(bloco_id=block.id, tipo_erro='CONCEITO', quantidade=classifications[index]))
            db.commit()
        response = client.get('/api/v1/performance/relatorio/mensal', params={'mes': 9, 'ano': 2026})
        assert response.status_code == 200, response.text
        return response.json()['erros']

    return read, engine


def test_missing_classifications_do_not_imply_improvement(report):
    read, engine = report
    errors = read([(10, 8), (10, 8)], [(10, 8), (10, 8)], classified_previous=[2, 2])
    assert errors['tendencia_erro'] == 'ESTÁVEL'
    assert errors['total_erros_observados'] == 4
    assert errors['total_erros_registrados'] == 0
    assert errors['cobertura_classificacao_percentual'] == 0
    assert errors['taxa_erro_observada_atual'] == errors['taxa_erro_observada_mes_anterior'] == 20
    with Session(engine) as db:
        assert db.query(models.BlocoQuestoes).count() == 4
        assert sum(row.quantidade for row in db.query(models.ErroQuestao)) == 4


@pytest.mark.parametrize('current,previous,expected', [
    ([(10, 9), (10, 9)], [(10, 5), (10, 5)], 'MELHORANDO'),
    ([(10, 5), (10, 5)], [(10, 9), (10, 9)], 'PIORANDO'),
    ([(100, 80), (50, 40)], [(10, 8), (10, 8)], 'ESTÁVEL'),
    ([(5, 4)], [(10, 8), (10, 8)], 'AMOSTRA_INSUFICIENTE'),
    ([(10, 8), (10, 8)], [(5, 4)], 'AMOSTRA_INSUFICIENTE'),
    ([], [(10, 8), (10, 8)], 'SEM_DADOS_ATUAIS'),
    ([(10, 8), (10, 8)], [], 'SEM_DADOS_ANTERIORES'),
    ([(10, 10), (10, 10)], [(10, 8), (10, 8)], 'MELHORANDO'),
    ([(10, 10), (10, 10)], [(10, 10), (10, 10)], 'ESTÁVEL'),
    ([(20, 17), (20, 17)], [(20, 16), (20, 16)], 'ESTÁVEL'),
])
def test_trend_uses_observed_weighted_rate_and_minimum_evidence(report, current, previous, expected):
    read, _ = report
    errors = read(current, previous)
    assert errors['tendencia_erro'] == expected
    assert errors['total_erros_registrados'] == 0
    assert errors['total_erros_observados'] == sum(total - hits for total, hits in current)
    assert errors['total_questoes_observadas'] == sum(total for total, _ in current)
    if not current:
        assert errors['taxa_erro_observada_atual'] is None
    if not previous:
        assert errors['taxa_erro_observada_mes_anterior'] is None
    if current and all(total == hits for total, hits in current):
        assert errors['taxa_erro_observada_atual'] == 0
        assert errors['cobertura_classificacao_percentual'] is None


def test_classification_coverage_is_separate_from_trend(report):
    read, _ = report
    errors = read([(10, 8), (10, 8)], [(10, 8), (10, 8)], classified_current=[1, 1])
    assert errors['tendencia_erro'] == 'ESTÁVEL'
    assert errors['cobertura_classificacao_percentual'] == 50
    # Legacy fields keep their classified-errors/block meaning.
    assert errors['erros_por_bloco_atual'] == 1
    assert not errors['classificacao_inconsistente']


def test_inconsistent_legacy_classification_is_flagged_not_rewritten(report):
    read, engine = report
    errors = read([(10, 10), (10, 10)], [(10, 10), (10, 10)], classified_current=[1])
    assert errors['tendencia_erro'] == 'ESTÁVEL'
    assert errors['classificacao_inconsistente']
    assert errors['total_erros_observados'] == 0
    assert errors['total_erros_registrados'] == 1
    with Session(engine) as db:
        assert db.query(models.ErroQuestao).one().quantidade == 1
