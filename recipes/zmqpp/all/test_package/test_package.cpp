#include <iostream>
#include <zmqpp/zmqpp.hpp>

int main(int argc, char *argv[]) {
    std::cout << zmqpp::version() << std::endl;
    zmqpp::context ctx; // throws on error
    return 0;
}
