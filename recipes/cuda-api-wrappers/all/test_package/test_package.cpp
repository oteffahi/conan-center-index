#include <cuda/define_specifiers.hpp>
#include <iostream>

CUDA_FH void test() {
    std::cout << "cuda-api-wrappers v" << CUDA_API_WRAPPERS_VERSION << std::endl;
}

int main() {
    test();
    return 0;
}
