# data-driven-brasileirao-insights# Data-Driven Brasileirão Insights

Plataforma Full Stack de análise estatística, Data Science e Machine Learning aplicada ao futebol brasileiro.

## Sobre o projeto

O Data-Driven Brasileirão Insights (DBI) é uma plataforma desenvolvida para coletar, processar, analisar e visualizar dados das principais competições do futebol brasileiro.

O projeto combina:

- Engenharia de Dados
- Desenvolvimento Full Stack
- Estatística
- Data Analytics
- Machine Learning
- Visualização de Dados

## Competições

- Campeonato Brasileiro Série A
- Campeonato Brasileiro Série B
- Campeonato Brasileiro Série C
- Campeonato Brasileiro Série D

## Arquitetura

```text
External Football APIs
        │
        ▼
Data Pipeline
        │
        ▼
Data Validation
        │
        ▼
Supabase / PostgreSQL
        │
        ├───────────────┐
        ▼               ▼
   Analytics           ML
        │               │
        └───────┬───────┘
                ▼
             FastAPI
                │
                ▼
              React