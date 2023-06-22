#include "picosha2.h"
#include <iostream>

void CalcAndOutput(const std::string &src) {
    std::cout << "src : \"" << src << "\"\n";
    std::cout << "hash: " << picosha2::hash256_hex_string(src) << "\n" << std::endl;
}

int main() {
    CalcAndOutput("");

    return 0;
}
