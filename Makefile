CXX = g++
CXXFLAGS = -std=c++17 -Wall -O2

all: client

client: client.cpp algHammingSnd.hpp algFletcherSnd.hpp
	$(CXX) $(CXXFLAGS) -o client client.cpp

server:
	python3 server.py

pruebas:
	cd pruebas && python3 pruebas_fletcher.py && python3 graficas.py

clean:
	rm -f client

.PHONY: all server pruebas clean
