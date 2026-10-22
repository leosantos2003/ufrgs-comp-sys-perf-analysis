#include "ga.hpp"

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

struct Arguments {
    ag::Config config{};
    ag::MeasurementMode mode = ag::MeasurementMode::Baseline;
    bool print_header = false;
};

[[noreturn]] void usage(const int status) {
    std::ostream& output = status == EXIT_SUCCESS ? std::cout : std::cerr;
    output << "Uso: ag_bench [opções]\n"
           << "  --population N       tamanho da população (padrão: 128)\n"
           << "  --length L           comprimento do cromossomo (padrão: 64)\n"
           << "  --generations G      gerações por execução (padrão: 100)\n"
           << "  --seed S              semente do mt19937_64 (padrão: 0)\n"
           << "  --crossover P         probabilidade de crossover [0,1] (padrão: 0.90)\n"
           << "  --mutation P          probabilidade de mutação por gene [0,1] (padrão: 0.01)\n"
           << "  --mode M              baseline ou phases (padrão: baseline)\n"
           << "  --header              imprime o cabeçalho CSV antes do resultado\n"
           << "  --help                mostra esta ajuda\n";
    std::exit(status);
}

std::string option_value(const int argc, char* argv[], int& index, const std::string& option) {
    if (index + 1 >= argc) {
        throw std::invalid_argument("faltou valor para " + option);
    }
    ++index;
    return argv[index];
}

std::size_t parse_size(const std::string& value, const std::string& option) {
    std::size_t consumed = 0;
    const auto parsed = std::stoull(value, &consumed);
    if (consumed != value.size()) {
        throw std::invalid_argument("valor inválido para " + option + ": " + value);
    }
    return static_cast<std::size_t>(parsed);
}

std::uint64_t parse_seed(const std::string& value) {
    std::size_t consumed = 0;
    const auto parsed = std::stoull(value, &consumed);
    if (consumed != value.size()) {
        throw std::invalid_argument("valor inválido para --seed: " + value);
    }
    return parsed;
}

double parse_probability(const std::string& value, const std::string& option) {
    std::size_t consumed = 0;
    const double parsed = std::stod(value, &consumed);
    if (consumed != value.size()) {
        throw std::invalid_argument("valor inválido para " + option + ": " + value);
    }
    return parsed;
}

Arguments parse_arguments(const int argc, char* argv[]) {
    Arguments arguments{};
    for (int index = 1; index < argc; ++index) {
        const std::string option = argv[index];
        if (option == "--help") {
            usage(EXIT_SUCCESS);
        }
        if (option == "--header") {
            arguments.print_header = true;
        } else if (option == "--population") {
            arguments.config.population_size = parse_size(option_value(argc, argv, index, option), option);
        } else if (option == "--length") {
            arguments.config.chromosome_length = parse_size(option_value(argc, argv, index, option), option);
        } else if (option == "--generations") {
            arguments.config.generations = parse_size(option_value(argc, argv, index, option), option);
        } else if (option == "--seed") {
            arguments.config.seed = parse_seed(option_value(argc, argv, index, option));
        } else if (option == "--crossover") {
            arguments.config.crossover_probability =
                parse_probability(option_value(argc, argv, index, option), option);
        } else if (option == "--mutation") {
            arguments.config.mutation_probability =
                parse_probability(option_value(argc, argv, index, option), option);
        } else if (option == "--mode") {
            const std::string mode = option_value(argc, argv, index, option);
            if (mode == "baseline") {
                arguments.mode = ag::MeasurementMode::Baseline;
            } else if (mode == "phases") {
                arguments.mode = ag::MeasurementMode::Phases;
            } else {
                throw std::invalid_argument("--mode deve ser baseline ou phases");
            }
        } else {
            throw std::invalid_argument("opção desconhecida: " + option);
        }
    }
    return arguments;
}

void print_header() {
    std::cout << "population_size,chromosome_length,generations,seed,crossover_probability,"
                 "mutation_probability,measurement_mode,elapsed_ns,evaluation_ns,selection_ns,"
                 "crossover_ns,mutation_ns,replacement_ns,best_fitness,checksum\n";
}

void print_result(const Arguments& arguments, const ag::RunResult& result) {
    std::cout << std::setprecision(17) << arguments.config.population_size << ','
              << arguments.config.chromosome_length << ',' << arguments.config.generations << ','
              << arguments.config.seed << ',' << arguments.config.crossover_probability << ','
              << arguments.config.mutation_probability << ',' << ag::to_string(arguments.mode) << ','
              << result.elapsed_ns << ',' << result.phase_timings.evaluation_ns << ','
              << result.phase_timings.selection_ns << ',' << result.phase_timings.crossover_ns << ','
              << result.phase_timings.mutation_ns << ',' << result.phase_timings.replacement_ns << ','
              << result.best_fitness << ',' << result.checksum << '\n';
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        const Arguments arguments = parse_arguments(argc, argv);
        const ag::RunResult result = ag::run(arguments.config, arguments.mode);
        if (arguments.print_header) {
            print_header();
        }
        print_result(arguments, result);
        return EXIT_SUCCESS;
    } catch (const std::exception& exception) {
        std::cerr << "erro: " << exception.what() << '\n';
        return EXIT_FAILURE;
    }
}
