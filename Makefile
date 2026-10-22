.DEFAULT_GOAL := help

.PHONY: help build test run clean

help:
	@printf '%s\n' 'Alvos disponíveis:'
	@printf '%s\n' '  make build  - compila ag_bench e ag_tests em build/'
	@printf '%s\n' '  make test   - compila e executa os testes determinísticos'
	@printf '%s\n' '  make run    - executa uma configuração pequena de demonstração'
	@printf '%s\n' '  make clean  - remove somente build/'

build:
	./scripts/build.sh

test: build
	./build/ag_tests

run: build
	./build/ag_bench --header --population 128 --length 64 --generations 100 --seed 0 --mode baseline

clean:
	rm -rf build
