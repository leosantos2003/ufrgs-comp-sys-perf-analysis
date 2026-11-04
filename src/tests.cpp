#include "ga.hpp"

#include <cstdlib>
#include <cstdint>
#include <exception>
#include <iostream>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

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

struct ReferenceRunResult {
    std::size_t best_fitness = 0;
    std::uint64_t checksum = 0;
};

std::size_t reference_one_max(const ag::Chromosome& chromosome) {
    std::size_t fitness = 0;
    for (const ag::Gene gene : chromosome) {
        fitness += static_cast<std::size_t>(gene);
    }
    return fitness;
}

std::size_t reference_tournament_winner(const std::vector<std::size_t>& fitness,
                                        const std::size_t first,
                                        const std::size_t second) {
    if (fitness[first] > fitness[second]) {
        return first;
    }
    if (fitness[second] > fitness[first]) {
        return second;
    }
    return first < second ? first : second;
}

std::uint64_t reference_population_checksum(const ag::Population& population) {
    std::uint64_t checksum = 1469598103934665603ULL;
    for (const auto& chromosome : population) {
        for (const ag::Gene gene : chromosome) {
            checksum ^= static_cast<std::uint64_t>(gene);
            checksum *= 1099511628211ULL;
        }
    }
    return checksum;
}

// Modelo deliberadamente simples e independente das primitivas de produção.
// Ele é usado somente em instâncias pequenas, para comparar o estado final
// produzido com a mesma sequência pseudoaleatória.
ReferenceRunResult reference_run(const ag::Config& config) {
    std::mt19937_64 random_engine(config.seed);
    std::bernoulli_distribution initial_gene(0.5);
    std::uniform_int_distribution<std::size_t> individual_index(0, config.population_size - 1);
    std::bernoulli_distribution should_crossover(config.crossover_probability);

    ag::Population population(config.population_size, ag::Chromosome(config.chromosome_length));
    ag::Population next_population(config.population_size, ag::Chromosome(config.chromosome_length));
    std::vector<std::size_t> fitness(config.population_size);
    std::vector<std::size_t> first_parents(config.population_size);
    std::vector<std::size_t> second_parents(config.population_size);

    for (auto& chromosome : population) {
        for (ag::Gene& gene : chromosome) {
            gene = static_cast<ag::Gene>(initial_gene(random_engine));
        }
    }

    const bool can_crossover = config.chromosome_length > 1;
    std::uniform_int_distribution<std::size_t> cut_point(0, 0);
    if (can_crossover) {
        cut_point = std::uniform_int_distribution<std::size_t>(1, config.chromosome_length - 1);
    }

    for (std::size_t generation = 0; generation < config.generations; ++generation) {
        for (std::size_t index = 0; index < config.population_size; ++index) {
            fitness[index] = reference_one_max(population[index]);
        }

        for (std::size_t index = 0; index < config.population_size; ++index) {
            first_parents[index] = reference_tournament_winner(
                fitness, individual_index(random_engine), individual_index(random_engine));
            second_parents[index] = reference_tournament_winner(
                fitness, individual_index(random_engine), individual_index(random_engine));
        }

        for (std::size_t index = 0; index < config.population_size; ++index) {
            const ag::Chromosome& first_parent = population[first_parents[index]];
            const ag::Chromosome& second_parent = population[second_parents[index]];
            ag::Chromosome& child = next_population[index];

            if (can_crossover && should_crossover(random_engine)) {
                const std::size_t cut = cut_point(random_engine);
                for (std::size_t gene_index = 0; gene_index < config.chromosome_length; ++gene_index) {
                    child[gene_index] = gene_index < cut ? first_parent[gene_index]
                                                         : second_parent[gene_index];
                }
            } else {
                for (std::size_t gene_index = 0; gene_index < config.chromosome_length; ++gene_index) {
                    child[gene_index] = first_parent[gene_index];
                }
            }
        }

        for (ag::Chromosome& child : next_population) {
            if (config.mutation_probability == 1.0) {
                for (ag::Gene& gene : child) {
                    gene = static_cast<ag::Gene>(1U - gene);
                }
            } else if (config.mutation_probability != 0.0) {
                std::bernoulli_distribution should_flip(config.mutation_probability);
                for (ag::Gene& gene : child) {
                    if (should_flip(random_engine)) {
                        gene = static_cast<ag::Gene>(1U - gene);
                    }
                }
            }
        }

        population.swap(next_population);
    }

    ReferenceRunResult result{};
    for (const auto& chromosome : population) {
        const std::size_t fitness_value = reference_one_max(chromosome);
        if (fitness_value > result.best_fitness) {
            result.best_fitness = fitness_value;
        }
    }
    result.checksum = reference_population_checksum(population);
    return result;
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

    ag::Chromosome first_controlled(16, 0);
    ag::Chromosome second_controlled(16, 0);
    std::mt19937_64 first_engine(20261103);
    std::mt19937_64 second_engine(20261103);
    ag::mutate_bit_flip(first_controlled, 0.5, first_engine);
    ag::mutate_bit_flip(second_controlled, 0.5, second_engine);
    expect(first_controlled == second_controlled,
           "mutação deve ser reprodutível para uma sequência aleatória controlada");
    expect(first_controlled == ag::Chromosome({1, 0, 1, 0, 0, 1, 1, 1,
                                               1, 0, 1, 1, 1, 0, 0, 0}),
           "a sequência controlada deve produzir os bit-flips esperados");
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

void test_against_simple_reference() {
    const std::vector<ag::Config> configurations{
        ag::Config{1, 1, 3, 0.0, 0.0, 7},
        ag::Config{2, 2, 5, 1.0, 1.0, 19},
        ag::Config{3, 7, 8, 0.35, 0.25, 20261022},
        ag::Config{16, 8, 10, 0.90, 0.01, 20261103},
    };

    for (const ag::Config& config : configurations) {
        const ag::RunResult implementation = ag::run(config, ag::MeasurementMode::Baseline);
        const ReferenceRunResult reference = reference_run(config);
        expect_equal(implementation.checksum, reference.checksum,
                     "checksum da implementação deve coincidir com a referência simples");
        expect_equal(implementation.best_fitness, reference.best_fitness,
                     "melhor fitness da implementação deve coincidir com a referência simples");
    }
}

void test_population_shape_and_fitness_after_each_generation() {
    ag::Config config{};
    config.population_size = 5;
    config.chromosome_length = 9;
    config.generations = 6;
    config.crossover_probability = 0.65;
    config.mutation_probability = 0.20;
    config.seed = 91;

    std::size_t observed_generations = 0;
    const ag::RunResult result = ag::run(
        config,
        ag::MeasurementMode::Baseline,
        [&config, &observed_generations](const std::size_t completed_generations,
                                         const ag::Population& population) {
            expect_equal(completed_generations, observed_generations + 1,
                         "o observador deve receber cada geração em ordem");
            expect_equal(population.size(), config.population_size,
                         "o tamanho da população deve permanecer constante");
            for (const ag::Chromosome& chromosome : population) {
                expect_equal(chromosome.size(), config.chromosome_length,
                             "o tamanho de cada cromossomo deve permanecer constante");
                std::size_t fitness = 0;
                for (const ag::Gene gene : chromosome) {
                    expect(gene == 0U || gene == 1U,
                           "todos os genes devem permanecer binários");
                    fitness += static_cast<std::size_t>(gene);
                }
                expect(fitness <= config.chromosome_length,
                       "o fitness de cada indivíduo deve ficar entre zero e L");
            }
            ++observed_generations;
        });

    expect_equal(observed_generations, config.generations,
                 "a população deve ser observada após todas as gerações");
    expect(result.best_fitness <= config.chromosome_length,
           "o melhor fitness final deve ficar no intervalo permitido");
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
        test_against_simple_reference();
        test_population_shape_and_fitness_after_each_generation();
        test_phase_mode();
        std::cout << "Todos os testes do AG passaram.\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& exception) {
        std::cerr << "Falha de teste: " << exception.what() << '\n';
        return EXIT_FAILURE;
    }
}
