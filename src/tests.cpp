#include "ga.hpp"

#include <cstdlib>
#include <exception>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {

void expect(const bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

template <typename Actual, typename Expected>
void expect_equal(const Actual& actual, const Expected& expected, const std::string& description) {
    if (actual != expected) {
        std::ostringstream message;
        message << description << ": esperado " << expected << ", obtido " << actual;
        throw std::runtime_error(message.str());
    }
}

template <typename Callable>
void expect_throws(Callable callable, const std::string& description) {
    try {
        callable();
    } catch (const std::exception&) {
        return;
    }
    throw std::runtime_error(description + ": exceção esperada não ocorreu");
}

void test_onemax() {
    expect_equal(ag::one_max(ag::Chromosome{1, 0, 1, 1, 0, 1}), std::size_t{4},
                 "OneMax deve contar os bits iguais a um");
    expect_throws([] { (void)ag::one_max(ag::Chromosome{0, 2}); },
                  "OneMax deve rejeitar gene não binário");
}

void test_tournament() {
    const std::vector<std::size_t> fitness{2, 7, 7, 4};
    expect_equal(ag::tournament_winner(fitness, 0, 1), std::size_t{1},
                 "o maior fitness deve vencer o torneio");
    expect_equal(ag::tournament_winner(fitness, 2, 1), std::size_t{1},
                 "empate deve usar o menor índice de forma determinística");
    expect_throws([&fitness] { (void)ag::tournament_winner(fitness, 0, 4); },
                  "torneio deve rejeitar índice inválido");
}

void test_crossover() {
    const ag::Chromosome first_parent{1, 0, 1, 0};
    const ag::Chromosome second_parent{0, 0, 0, 1};
    ag::Chromosome child(4);
    ag::crossover_one_point(first_parent, second_parent, 2, child);
    expect(child == ag::Chromosome({1, 0, 0, 1}),
           "crossover deve copiar prefixo do primeiro pai e sufixo do segundo");
    expect_throws([&] { ag::crossover_one_point(first_parent, second_parent, 0, child); },
                  "crossover deve rejeitar corte zero");
    expect_throws([&] { ag::crossover_one_point(first_parent, second_parent, 4, child); },
                  "crossover deve rejeitar corte no fim do cromossomo");
}

void test_mutation() {
    std::mt19937_64 random_engine(42);
    ag::Chromosome chromosome{1, 0, 0, 1};
    ag::mutate_bit_flip(chromosome, 0.0, random_engine);
    expect(chromosome == ag::Chromosome({1, 0, 0, 1}),
           "mutação com probabilidade zero não pode alterar o cromossomo");
    ag::mutate_bit_flip(chromosome, 1.0, random_engine);
    expect(chromosome == ag::Chromosome({0, 1, 1, 0}),
           "mutação com probabilidade um deve inverter todos os genes");
}

void test_configuration_validation() {
    ag::Config config{};
    config.population_size = 0;
    expect_throws([&config] { ag::validate_config(config); },
                  "população vazia deve ser rejeitada");

    config = ag::Config{};
    config.chromosome_length = 0;
    expect_throws([&config] { ag::validate_config(config); },
                  "cromossomo vazio deve ser rejeitado");

    config = ag::Config{};
    config.mutation_probability = 1.1;
    expect_throws([&config] { ag::validate_config(config); },
                  "probabilidade acima de um deve ser rejeitada");
}

void test_deterministic_run() {
    ag::Config config{};
    config.population_size = 32;
    config.chromosome_length = 16;
    config.generations = 10;
    config.crossover_probability = 0.90;
    config.mutation_probability = 0.01;
    config.seed = 20261022;

    const ag::RunResult first = ag::run(config, ag::MeasurementMode::Baseline);
    const ag::RunResult second = ag::run(config, ag::MeasurementMode::Baseline);

    expect_equal(first.checksum, second.checksum,
                 "mesma configuração e semente devem produzir o mesmo checksum");
    expect_equal(first.best_fitness, second.best_fitness,
                 "mesma configuração e semente devem produzir o mesmo melhor fitness");
    expect(first.best_fitness <= config.chromosome_length,
           "melhor fitness deve estar no intervalo permitido");
    expect(first.elapsed_ns > 0, "execução medida deve ter duração positiva");
}

void test_phase_mode() {
    ag::Config config{};
    config.population_size = 64;
    config.chromosome_length = 64;
    config.generations = 5;
    config.seed = 9;

    const ag::RunResult baseline = ag::run(config, ag::MeasurementMode::Baseline);
    const ag::RunResult result = ag::run(config, ag::MeasurementMode::Phases);
    const std::uint64_t phase_sum = result.phase_timings.evaluation_ns +
                                    result.phase_timings.selection_ns +
                                    result.phase_timings.crossover_ns +
                                    result.phase_timings.mutation_ns +
                                    result.phase_timings.replacement_ns;
    expect(result.elapsed_ns >= phase_sum,
           "tempo total deve incluir pelo menos a soma das fases instrumentadas");
    expect_equal(result.checksum, baseline.checksum,
                 "instrumentação por fases não pode alterar a evolução do AG");
    expect_equal(result.best_fitness, baseline.best_fitness,
                 "instrumentação por fases não pode alterar o melhor fitness");
}

}  // namespace

int main() {
    try {
        test_onemax();
        test_tournament();
        test_crossover();
        test_mutation();
        test_configuration_validation();
        test_deterministic_run();
        test_phase_mode();
        std::cout << "Todos os testes do AG passaram.\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& exception) {
        std::cerr << "Falha de teste: " << exception.what() << '\n';
        return EXIT_FAILURE;
    }
}
