#include <iostream>
#include <nanorange.hpp>

int main() {
    int elems[] = {0, 42, 666};
    return *nano::min_element(elems);
}
