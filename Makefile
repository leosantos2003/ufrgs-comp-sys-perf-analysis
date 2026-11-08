.DEFAULT_GOAL := help

.PHONY: help build test run environment design check-design pilot check-pilot calibrate-remaining check-calibrate-remaining baseline check-baseline clean

help:
	@printf '%s\n' 'Alvos disponíveis:'
	@printf '%s\n' '  make build  - compila ag_bench e ag_tests em build/'
	@printf '%s\n' '  make test   - compila e executa os testes determinísticos'
	@printf '%s\n' '  make run    - executa uma configuração pequena de demonstração'
	@printf '%s\n' '  make environment - captura inventário e testa taskset/perf'
	@printf '%s\n' '  make design - gera e valida o DOE em config/design.csv'
	@printf '%s\n' '  make check-design - verifica o DOE sem regravá-lo'
	@printf '%s\n' '  make pilot - executa o piloto de três pontos e recomenda B'
	@printf '%s\n' '  make check-pilot - valida a configuração do piloto sem medir'
	@printf '%s\n' '  make calibrate-remaining - calibra B nas combinações da grade fora do piloto'
	@printf '%s\n' '  make check-calibrate-remaining - valida essa calibração sem medir'
	@printf '%s\n' '  make baseline - captura o ambiente e executa a campanha baseline completa'
	@printf '%s\n' '  make check-baseline - valida a campanha baseline sem medir'
	@printf '%s\n' '  make clean  - remove somente build/'

build:
	./scripts/build.sh

test: build
	./build/ag_tests

run: build
	./build/ag_bench --header --population 128 --length 64 --generations 100 --seed 0 --mode baseline

environment: build
	./scripts/capture_environment.sh

design:
	./scripts/generate_design.py

check-design:
	./scripts/generate_design.py --check

pilot: build
	python3 ./scripts/calibrate_batch.py

check-pilot: build
	python3 ./scripts/calibrate_batch.py --dry-run

calibrate-remaining: build
	python3 ./scripts/calibrate_batch.py --remaining-grid

check-calibrate-remaining: build
	python3 ./scripts/calibrate_batch.py --remaining-grid --dry-run

baseline: build
	python3 ./scripts/run_experiments.py

check-baseline: build
	python3 ./scripts/run_experiments.py --dry-run

clean:
	rm -rf build
