PYTHON ?= python3
PIP ?= /home/kyz/.local/bin/pip3

SCRIPT := ./scripts/generate-cheatsheet.sh

export PYTHON
export PIP

.PHONY: all deps generate bundle verify

all: generate bundle verify

deps:
	$(SCRIPT) deps

generate:
	$(SCRIPT) generate

bundle:
	$(SCRIPT) bundle

verify:
	$(SCRIPT) verify
