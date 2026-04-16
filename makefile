# SHELL := /usr/bin/env bash

.PHONY: lab01-up
lab01-up:
	docker-compose -f lab01/docker-compose.yml up --build

.PHONY: lab01-tests
lab01-tests: 
	pytest lab01/backend/app/tests/test_domain.py -v

.PHONY: lab01-tests-invariant
lab01-tests-invariant: 
	pytest lab01/backend/app/tests/test_domain.py::TestCriticalPaymentInvariant -v