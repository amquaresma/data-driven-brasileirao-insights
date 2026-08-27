# Architecture Overview

## Objective

The Data-Driven Brasileirão Insights platform is designed as a modular system combining Full Stack development, Data Engineering, Statistical Analytics and Machine Learning.

## High-Level Architecture

```text
                    Football APIs
                         │
                         ▼
                ┌─────────────────┐
                │ Data Ingestion  │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Data Validation │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │  PostgreSQL     │
                │    Supabase     │
                └────────┬────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
       ┌──────────────┐      ┌──────────────┐
       │   Analytics  │      │      ML      │
       └──────┬───────┘      └──────┬───────┘
              │                     │
              └──────────┬──────────┘
                         ▼
                   ┌───────────┐
                   │  FastAPI  │
                   └─────┬─────┘
                         │
                         ▼
                   ┌───────────┐
                   │   React   │
                   └───────────┘