cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

add_executable(${PROJECT_NAME} test_package.cpp)
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_11)
