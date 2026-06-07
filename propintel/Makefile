-include .env
export

.PHONY: help install ingest-all convert dbt-build dbt-test pipeline test api frontend-streamlit

help:
	@echo "install              pip install -e .[dev]"
	@echo "ingest-all           fetch all data sources"
	@echo "convert              convert raw files to parquet/geoparquet"
	@echo "dbt-build            run dbt build (from dbt/)"
	@echo "dbt-test             run dbt test (from dbt/)"
	@echo "pipeline             ingest-all → convert → dbt-build"
	@echo "test                 run pytest"
	@echo "api                  start FastAPI dev server"
	@echo "frontend-streamlit   start Streamlit map"

install:
	pip install -e ".[dev]"

ingest-all:
	python -m ingestion.run all

convert:
	python -m ingestion.run convert

dbt-build:
	cd dbt && dbt build

dbt-test:
	cd dbt && dbt test

pipeline: ingest-all convert dbt-build

test:
	pytest tests/ -v

api:
	uvicorn api.main:app --reload

frontend-streamlit:
	streamlit run frontend/map.py
