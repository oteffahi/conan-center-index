cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(cassandra-cpp-driver REQUIRED CONFIG)

add_executable(${PROJECT_NAME} main.cpp)

target_link_libraries(${PROJECT_NAME} cassandra-cpp-driver::cassandra-cpp-driver)
