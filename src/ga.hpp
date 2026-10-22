#pragma once

#include <cstddef>
#include <cstdint>
#include <random>
#include <vector>

namespace ag {

using Gene = std::uint8_t;
using Chromosome = std::vector<Gene>;
using Population = std::vector<Chromosome>;

struct Config {
    std::size_t population_size = 128;
    std::size_t chromosome_length = 64;
    std::size_t generations = 100;
    double crossover_probability = 0.90;
    double mutation_probability = 0.01;
    std::uint64_t seed = 0;
};

enum class MeasurementMode {
    Baseline,
    Phases,
};

struct PhaseTimings {
    std::uint64_t evaluation_ns = 0;
    std::uint64_t selection_ns = 0;
    std::uint64_t crossover_ns = 0;
    std::uint64_t mutation_ns = 0;
    std::uint64_t replacement_ns = 0;
};

struct RunResult {
    std::uint64_t elapsed_ns = 0;
    PhaseTimings phase_timings{};
    std::size_t best_fitness = 0;
    std::uint64_t checksum = 0;
};

void validate_config(const Config& config);

std::size_t one_max(const Chromosome& chromosome);

std::size_t tournament_winner(const std::vector<std::size_t>& fitness,
                              std::size_t first,
                              std::size_t second);

void crossover_one_point(const Chromosome& first_parent,
                         const Chromosome& second_parent,
                         std::size_t cut_point,
                         Chromosome& child);

void mutate_bit_flip(Chromosome& chromosome,
                     double probability_per_gene,
                     std::mt19937_64& random_engine);

RunResult run(const Config& config, MeasurementMode mode);

const char* to_string(MeasurementMode mode);

}  // namespace ag
