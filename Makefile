CXX      = g++
CXXFLAGS = -O3 -std=c++17 -Wall -Wextra

all: bin/disease_seq bin/disease_omp

bin:
	mkdir -p bin

bin/disease_seq: src/disease_seq.cpp src/sim_common.hpp | bin
	$(CXX) $(CXXFLAGS) $< -o $@

bin/disease_omp: src/disease_omp.cpp src/sim_common.hpp | bin
	$(CXX) $(CXXFLAGS) -fopenmp $< -o $@

test: all
	python3 scripts/verify.py

bench: all test
	python3 scripts/run_benchmarks.py

report:
	python3 scripts/make_report.py

clean:
	rm -rf bin

.PHONY: all test bench report clean
