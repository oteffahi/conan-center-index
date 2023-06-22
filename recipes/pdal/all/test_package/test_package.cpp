#include <iostream>
#include <pdal/PluginManager.hpp>
#include <pdal/StageFactory.hpp>
#include <pdal/pdal_config.hpp>

int main() {
    std::cout << pdal::Config::fullVersionString() << std::endl;
    std::cout << pdal::Config::debugInformation() << std::endl;

    std::cout << "Available plugins:" << std::endl;
    for (auto const &name : pdal::PluginManager<pdal::Stage>::names()) {
        std::cout << "- " << name << std::endl;
    }

    return 0;
}
