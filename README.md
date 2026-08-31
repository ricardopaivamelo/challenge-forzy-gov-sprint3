# Challenge Forzy — Governança da Decisão

Repositório da **Challenge Sprint 3 de GBA/GOV** da FIAP: Inteligência Operacional e
Governança da Decisão para o Digital Twin Forzy.

Este projeto é separado do repositório técnico de GenAI, que fornece o contexto dos alertas
de anomalia:

<https://github.com/ricardopaivamelo/challenge-forzy-genai-sprint3>

## Escopo

O trabalho não treina novamente o detector de anomalias. Ele governa a decisão produzida pelo
modelo: valida métricas de temperatura, vibração e aceleração, classifica estados, bloqueia
alertas quando a qualidade ou a confiança são insuficientes e encaminha casos críticos para
revisão humana.

O protótipo é acadêmico e usa cenários determinísticos. Ele não autoriza parada automática de
motor ou planta.

## Demonstração

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

A aplicação apresenta cinco cenários:

- operação normal;
- faixa de atenção;
- anomalia persistente com handoff humano;
- Circuit Breaker por dado inválido;
- handoff por baixa confiança.

Também é possível selecionar o cenário por URL, por exemplo:

```text
http://localhost:8501/?scenario=Anomalia%20confirmada
```

## Conteúdo acadêmico

- `docs/gov/sprint3_documento_vivo.md`: documentação viva da evolução da governança;
- `docs/gov/metric_contracts.md`: contratos de temperatura, vibração e aceleração;
- `docs/gov/roteiro_video.md`: roteiro para o vídeo de 3–5 minutos;
- `docs/gov/matriz_supervisao_PREENCHER_PELO_GRUPO.md`: matriz autoral para revisão do grupo;
- `docs/gov/conclusao_PREENCHER_PELO_GRUPO.md`: conclusão autoral para revisão do grupo;
- `docs/gov/*.docx`: documentos prontos para inspeção e entrega;
- `figuras/gov_*.png`: evidências visuais catalogáveis.

Os textos da matriz de supervisão e da conclusão devem ser conferidos e aprovados pelo grupo,
pois representam a reflexão autoral exigida pelo barema.

## Implementação

- `src/governance_contracts.py`: contratos versionados e classificação dos sensores;
- `src/governance_service.py`: decisão determinística, Circuit Breaker e handoff;
- `src/demo_scenarios.py`: cenários fixos para demonstração e gravação;
- `src/dashboard_data.py`: adaptação dos fatos para tabela e registro auditável;
- `src/acceleration.py`: variável de aceleração derivada para o protótipo;
- `config/metric_contracts.json`: fonte operacional dos limites;
- `scripts/build_gov_documents.py`: gerador dos documentos Word.

## Verificação

```bash
.venv/bin/python -m pytest -x -vv -p no:cacheprovider tests
```

Os testes verificam os contratos, os limites, a qualidade dos dados, os bloqueios, o handoff,
os cinco cenários e o smoke test da aplicação.

## Limites e responsabilidade

- os dados e cenários são sintéticos;
- a aceleração é derivada da vibração no protótipo, não uma medição de acelerômetro;
- os limites precisam ser recalibrados antes de qualquer uso industrial;
- score e threshold do modelo vêm da GenAI Sprint 3 e são apenas insumos para governança;
- alerta significa prioridade de inspeção, não diagnóstico físico;
- parada de motor ou planta exige decisão humana e não pode ser disparada automaticamente.
