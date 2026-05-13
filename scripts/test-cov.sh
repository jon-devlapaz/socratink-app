#!/usr/bin/env bash

# Run tests with coverage reporting
pytest --cov=api --cov=auth --cov=db --cov=llm --cov=models --cov=source_intake --cov-report=xml --cov-report=term-missing --cov-branch "$@"
