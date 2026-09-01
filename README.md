# Challenge Sprint 3 — Governança em IA e Business Analytics (GOV)

[![tests](https://github.com/ricardopaivamelo/challenge-forzy-gov-sprint3/actions/workflows/tests.yml/badge.svg)](https://github.com/ricardopaivamelo/challenge-forzy-gov-sprint3/actions/workflows/tests.yml)

Entrega da FIAP para o tema **Inteligência Operacional e Governança da Decisão**, aplicada ao
Digital Twin Forzy. O repositório formaliza limites de interpretação, implementa o Circuit
Breaker e define quando a decisão deve ser transferida para um especialista.

## Separação entre GOV e GenAI

Este é o repositório de **GOV**. Ele não contém banco de treinamento, notebooks, modelos ou a
entrega acadêmica de GenAI. O score do detector é somente um insumo externo governado por este
projeto.

A origem imutável utilizada é o arquivo
[`models/anomaly_metrics.json`](https://github.com/ricardopaivamelo/challenge-forzy-genai-sprint3/blob/7ff33d0839593e0f49bf55d70e33b6bc4b25c08e/models/anomaly_metrics.json),
no commit `7ff33d0839593e0f49bf55d70e33b6bc4b25c08e`. O threshold exato do Autoencoder é
`0.9512501159120564`, exibido como `0.9513`. O Autoencoder foi adotado no demonstrador por seu
menor falso positivo entre os detectores de anomalia e pela interpretação do erro de
reconstrução; o relatório de origem identifica o método estatístico como melhor modelo geral.
Essa escolha, portanto, não é apresentada como ranking absoluto.

Os detalhes auditáveis estão em [`results/provenance.json`](results/provenance.json).

## O que a aplicação executa

- classifica temperatura, vibração e aceleração segundo Metric Contracts versionados;
- compara o score com o threshold exato e exige persistência de três janelas;
- bloqueia a decisão diante de dado inválido, incompleto, atrasado, incompatível ou incerto;
- registra o motivo do Circuit Breaker e preserva as evidências;
- cria handoff para o Engenheiro de Manutenção e persiste a decisão em um histórico JSONL local;
- nunca comanda parada física do motor ou da planta.

Os parâmetros operacionais ficam centralizados em [`config/decision_policy.json`](config/decision_policy.json)
e [`config/metric_contracts.json`](config/metric_contracts.json).

## Executar localmente

Requer Python 3.12.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

A aplicação oferece cinco cenários reproduzíveis: operação normal, atenção, anomalia confirmada,
Circuit Breaker por dado inválido e handoff por baixa confiança. O tema escuro é o padrão e pode
ser trocado pela barra lateral. As validações humanas registradas pela interface são acrescentadas
em `runtime/handoff_audit.jsonl`; essa pasta de execução não é versionada no Git.

## Entregáveis acadêmicos

- [`docs/entrega/challenge_sprint3_gov.pdf`](docs/entrega/challenge_sprint3_gov.pdf): documento final para leitura;
- [`docs/entrega/challenge_sprint3_gov.docx`](docs/entrega/challenge_sprint3_gov.docx): versão editável;
- [`docs/entrega/metric_contracts.pdf`](docs/entrega/metric_contracts.pdf): Metric Contracts formalizados;
- [`docs/entrega/metric_contracts.docx`](docs/entrega/metric_contracts.docx): versão editável;
- [`docs/gov/sprint3_documento_vivo.md`](docs/gov/sprint3_documento_vivo.md): fonte textual do documento vivo;
- [`docs/gov/matriz_supervisao.md`](docs/gov/matriz_supervisao.md): matriz autoral aprovada pelo grupo;
- [`docs/gov/consideracoes_finais.md`](docs/gov/consideracoes_finais.md): visão crítica aprovada pelo grupo;
- [`docs/gov/roteiro_video.md`](docs/gov/roteiro_video.md): roteiro de defesa de 3–5 minutos;
- [`docs/historico/sprint2_mockup.html`](docs/historico/sprint2_mockup.html): mockup histórico preservado;
- [`figuras/`](figuras): evidências catalogadas no padrão FIAP.

### Vídeo de defesa

**Pendente de gravação e envio pelo grupo.** O vídeo deve demonstrar a aplicação por 3–5 minutos;
nenhum link fictício foi inserido. Após o upload, basta acrescentar aqui o endereço definitivo.

## Regenerar os documentos

O documento vivo é autocontido:

```bash
python scripts/build_gov_documents.py
```

Para regerar também o Metric Contract com o modelo fornecido pelo professor, informe o arquivo
explicitamente; o modelo não é redistribuído neste repositório:

```bash
python scripts/build_gov_documents.py \
  --metric-template "/caminho/para/modelo-do-professor.docx"
```

## Verificação

```bash
python -m pytest -q
python -m pip check
python scripts/build_gov_documents.py --main-output /tmp/challenge_sprint3_gov.docx
```

Os testes cobrem fronteiras dos thresholds, política de decisão, qualidade dos dados, Circuit
Breaker, handoff, cinco cenários, dashboard e geração portátil do DOCX. O workflow do GitHub
executa a mesma suíte em Python 3.12 para cada pull request.

## Limitações declaradas

- os dados e os cenários são sintéticos;
- a aceleração é derivada da vibração, não medida por acelerômetro industrial;
- temperatura e vibração usam faixas empíricas do protótipo;
- todos os limites exigem recalibração e validação antes de uso industrial;
- anomalia indica prioridade de inspeção, não diagnóstico causal;
- contexto como manutenção recente, mudança de carga e ruído externo permanece sob análise humana.
