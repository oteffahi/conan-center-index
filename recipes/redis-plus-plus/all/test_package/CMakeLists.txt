cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(redis++ REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
if(TARGET redis++::redis++_static)
    target_link_libraries(${PROJECT_NAME} PRIVATE redis++::redis++_static)
else()
    target_link_libraries(${PROJECT_NAME} PRIVATE redis++::redis++)
endif()

if(NOT CMAKE_CXX_STANDARD)
    # Cover the case where compiler.cppstd is not defined in the Conan profile
    # (e.g. Conan 1.x), and define the compiler standard assuming the library defaults instead
    if(redis++_VERSION VERSION_GREATER_EQUAL "1.3.0")
        target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_17)
    else()
        # no target_compile_features here because redis-plus-plus < 1.3.0 is built
        # with C++11 by default and is not ABI compatible if consumed with C++17...
        set_target_properties(${PROJECT_NAME} PROPERTIES CXX_STANDARD 11)
    endif()
endif()
