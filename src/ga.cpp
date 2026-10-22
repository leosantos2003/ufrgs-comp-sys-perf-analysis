#include "ga.hpp"

#include <algorithm>
#include <chrono>
#include <limits>
#include <stdexcept>
#include <string>

namespace ag {
namespace {

using Clock = std::chrono::steady_clock;

std::uint64_t elapsed_nanoseconds(const Clock::time_point& start,
                                  const Clock::time_point& finish) {
    const auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(finish - start);
    return static_cast<std::uint64_t>(duration.count());
}

bool is_probability(const double value) {
    return value >= 0.0 && value <= 1.0;
}

void evaluate_population(const Population& population, std::vector<std::size_t>& fitness) {
    for (std::size_t index = 0; index < population.size(); ++index) {
        fitness[index] = one_max(population[index]);
    }
}

std::uint64_t population_checksum(const Population& population) {
    // FNV-1a: checksum simples, estável e suficiente para detectar mudanças acidentais.
    std::uint64_t checksum = 1469598103934665603ULL;
    for (const auto& chromosome : population) {
        for (const Gene gene : chromosome) {
            checksum ^= static_cast<std::uint64_t>(gene);
            checksum *= 1099511628211ULL;
        }
    }
    return checksum;
}

}  // namespace

void validate_config(const Config& config) {
    if (config.population_size == 0) {
        throw std::invalid_argument("population_size deve ser maior que zero");
    }
    if (config.chromosome_length == 0) {
        throw std::invalid_argument("chromosome_length deve ser maior que zero");
    }
    if (config.generations == 0) {
        throw std::invalid_argument("generations deve ser maior que zero");
    }
    if (!is_probability(config.crossover_probability)) {
        throw std::invalid_argument("crossover_probability deve estar entre 0 e 1");
    }
    if (!is_probability(config.mutation_probability)) {
        throw std::invalid_argument("mutation_probability deve estar entre 0 e 1");
    }
}

std::size_t one_max(const Chromosome& chromosome) {
    std::size_t fitness = 0;
    for (const Gene gene : chromosome) {
        if (gene > 1U) {
            throw std::invalid_argument("cromossomo contém gene que não é binário");
        }
        fitness += static_cast<std::size_t>(gene);
    }
    return fitness;
}

std::size_t tournament_winner(const std::vector<std::size_t>& fitness,
                              const std::size_t first,
                              const std::size_t second) {
    if (first >= fitness.size() || second >= fitness.size()) {
        throw std::out_of_range("índice de torneio fora da população");
    }

    if (fitness[first] > fitness[second]) {
        return first;
    }
    if (fitness[second] > fitness[first]) {
        return second;
    }
    // Desempate determinístico: o menor índice vence.
    return std::min(first, second);
}

void crossover_one_point(const Chromosome& first_parent,
                         const Chromosome& second_parent,
                         const std::size_t cut_point,
                         Chromosome& child) {
    if (first_parent.size() != second_parent.size() || child.size() != first_parent.size()) {
        throw std::invalid_argument("crossover requer cromossomos com o mesmo tamanho pré-alocado");
    }
    if (cut_point == 0 || cut_point >= first_parent.size()) {
        throw std::out_of_range("ponto de corte deve estar entre 1 e L - 1");
    }

    std::copy_n(first_parent.begin(), static_cast<std::ptrdiff_t>(cut_point), child.begin());
    std::copy(second_parent.begin() + static_cast<std::ptrdiff_t>(cut_point),
              second_parent.end(),
              child.begin() + static_cast<std::ptrdiff_t>(cut_point));
}

void mutate_bit_flip(Chromosome& chromosome,
                     const double probability_per_gene,
                     std::mt19937_64& random_engine) {
    if (!is_probability(probability_per_gene)) {
        throw std::invalid_argument("probability_per_gene deve estar entre 0 e 1");
    }
    if (probability_per_gene == 0.0) {
        return;
    }
    if (probability_per_gene == 1.0) {
        for (Gene& gene : chromosome) {
            gene = static_cast<Gene>(1U - gene);
        }
        return;
    }

    std::bernoulli_distribution should_flip(probability_per_gene);
    for (Gene& gene : chromosome) {
        if (gene > 1U) {
            throw std::invalid_argument("cromossomo contém gene que não é binário");
        }
        if (should_flip(random_engine)) {
            gene = static_cast<Gene>(1U - gene);
        }
    }
}

RunResult run(const Config& config, const MeasurementMode mode) {
    validate_config(config);

    std::mt19937_64 random_engine(config.seed);
    std::bernoulli_distribution initial_gene(0.5);
    std::uniform_int_distribution<std::size_t> individual_index(0, config.population_size - 1);
    std::bernoulli_distribution should_crossover(config.crossover_probability);

    Population population(config.population_size, Chromosome(config.chromosome_length));
    Population next_population(config.population_size, Chromosome(config.chromosome_length));
    std::vector<std::size_t> fitness(config.population_size);
    std::vector<std::size_t> first_parents(config.population_size);
    std::vector<std::size_t> second_parents(config.population_size);

    for (auto& chromosome : population) {
        for (Gene& gene : chromosome) {
            gene = static_cast<Gene>(initial_gene(random_engine));
        }
    }

    // Todas as estruturas de tamanho dependente de N e L foram alocadas acima.
    // A região medida contém exclusivamente as G gerações do AG.
    std::uniform_int_distribution<std::size_t> cut_point(0, 0);
    const bool can_crossover = config.chromosome_length > 1;
    if (can_crossover) {
        cut_point = std::uniform_int_distribution<std::size_t>(1, config.chromosome_length - 1);
    }

    RunResult result{};
    const auto total_start = Clock::now();

    for (std::size_t generation = 0; generation < config.generations; ++generation) {
        if (mode == MeasurementMode::Phases) {
            const auto phase_start = Clock::now();
            evaluate_population(population, fitness);
            result.phase_timings.evaluation_ns += elapsed_nanoseconds(phase_start, Clock::now());
        } else {
            evaluate_population(population, fitness);
        }

        if (mode == MeasurementMode::Phases) {
            const auto phase_start = Clock::now();
            for (std::size_t index = 0; index < config.population_size; ++index) {
                first_parents[index] = tournament_winner(
                    fitness, individual_index(random_engine), individual_index(random_engine));
                second_parents[index] = tournament_winner(
                    fitness, individual_index(random_engine), individual_index(random_engine));
            }
            result.phase_timings.selection_ns += elapsed_nanoseconds(phase_start, Clock::now());
        } else {
            for (std::size_t index = 0; index < config.population_size; ++index) {
                first_parents[index] = tournament_winner(
                    fitness, individual_index(random_engine), individual_index(random_engine));
                second_parents[index] = tournament_winner(
                    fitness, individual_index(random_engine), individual_index(random_engine));
            }
        }

        if (mode == MeasurementMode::Phases) {
            const auto phase_start = Clock::now();
            for (std::size_t index = 0; index < config.population_size; ++index) {
                const Chromosome& first_parent = population[first_parents[index]];
                const Chromosome& second_parent = population[second_parents[index]];
                Chromosome& child = next_population[index];
                if (can_crossover && should_crossover(random_engine)) {
                    crossover_one_point(first_parent, second_parent, cut_point(random_engine), child);
                } else {
                    std::copy(first_parent.begin(), first_parent.end(), child.begin());
                }
            }
            result.phase_timings.crossover_ns += elapsed_nanoseconds(phase_start, Clock::now());
        } else {
            for (std::size_t index = 0; index < config.population_size; ++index) {
                const Chromosome& first_parent = population[first_parents[index]];
                const Chromosome& second_parent = population[second_parents[index]];
                Chromosome& child = next_population[index];
                if (can_crossover && should_crossover(random_engine)) {
                    crossover_one_point(first_parent, second_parent, cut_point(random_engine), child);
                } else {
                    std::copy(first_parent.begin(), first_parent.end(), child.begin());
                }
            }
        }

        if (mode == MeasurementMode::Phases) {
            const auto phase_start = Clock::now();
            for (Chromosome& child : next_population) {
                mutate_bit_flip(child, config.mutation_probability, random_engine);
            }
            result.phase_timings.mutation_ns += elapsed_nanoseconds(phase_start, Clock::now());
        } else {
            for (Chromosome& child : next_population) {
                mutate_bit_flip(child, config.mutation_probability, random_engine);
            }
        }

        if (mode == MeasurementMode::Phases) {
            const auto phase_start = Clock::now();
            population.swap(next_population);
            result.phase_timings.replacement_ns += elapsed_nanoseconds(phase_start, Clock::now());
        } else {
            population.swap(next_population);
        }
    }

    result.elapsed_ns = elapsed_nanoseconds(total_start, Clock::now());

    // Estes cálculos são deliberadamente posteriores à região medida.
    result.best_fitness = 0;
    for (const auto& chromosome : population) {
        result.best_fitness = std::max(result.best_fitness, one_max(chromosome));
    }
    result.checksum = population_checksum(population);
    return result;
}

const char* to_string(const MeasurementMode mode) {
    switch (mode) {
        case MeasurementMode::Baseline:
            return "baseline";
        case MeasurementMode::Phases:
            return "phases";
    }
    return "unknown";
}

}  // namespace ag
