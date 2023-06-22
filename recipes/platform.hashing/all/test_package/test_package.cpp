#include <Platform.Hashing.h>

#include <any>
#include <array>
#include <iostream>
#include <vector>

using namespace Platform::Hashing;

auto main() -> int {
    std::cout << Hash(std::any{1}) << std::endl;
    std::cout << Hash(std::any{1}, std::any{1}) << std::endl;
    std::cout << Hash(std::vector{1}) << std::endl;
    std::cout << Hash(std::array{1}) << std::endl;
}
