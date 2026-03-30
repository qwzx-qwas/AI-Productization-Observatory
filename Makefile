PYTHON ?= python3
WINDOW ?=
SOURCE ?= product_hunt
QUERY_SLICE ?=

.PHONY: install lint format typecheck test validate-schemas validate-configs validate-gold-set validate-candidate-workspace validate-env replay-window build-mart-window migrate-plan run-candidate-prescreen handoff-candidates-to-staging

install:
	$(PYTHON) -m src.cli install

lint:
	$(PYTHON) -m src.cli lint

format:
	$(PYTHON) -m src.cli format

typecheck:
	$(PYTHON) -m src.cli typecheck

test:
	$(PYTHON) -m unittest discover -s tests -t .

validate-schemas:
	$(PYTHON) -m src.cli validate-schemas

validate-configs:
	$(PYTHON) -m src.cli validate-configs

validate-gold-set:
	$(PYTHON) -m src.cli validate-gold-set $(if $(REQUIRE_IMPLEMENTED),--require-implemented,)

validate-candidate-workspace:
	$(PYTHON) -m src.cli validate-candidate-workspace

validate-env:
	$(PYTHON) -m src.cli validate-env --require APO_CONFIG_DIR APO_SCHEMA_DIR

replay-window:
	@if [ -z "$(WINDOW)" ]; then echo "WINDOW is required, for example 2026-03-01..2026-03-08"; exit 2; fi
	$(PYTHON) -m src.cli replay-window --source $(SOURCE) --window $(WINDOW)

build-mart-window:
	$(PYTHON) -m src.cli build-mart-window

migrate-plan:
	$(PYTHON) -m src.cli migrate --plan

run-candidate-prescreen:
	@if [ -z "$(WINDOW)" ]; then echo "WINDOW is required, for example 2026-03-01..2026-03-08"; exit 2; fi
	$(PYTHON) -m src.cli run-candidate-prescreen --source $(SOURCE) --window $(WINDOW) $(if $(QUERY_SLICE),--query-slice $(QUERY_SLICE),)

handoff-candidates-to-staging:
	$(PYTHON) -m src.cli handoff-candidates-to-staging
