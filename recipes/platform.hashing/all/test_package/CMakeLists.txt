cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

set(EXTRA_FLAGS "" CACHE STRING "Extra compiler flags")
separate_arguments(EXTRA_FLAGS UNIX_COMMAND ${EXTRA_FLAGS})
if(EXTRA_FLAGS)
    add_compile_options(${EXTRA_FLAGS})
endif()

find_package(platform.hashing REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE platform.hashing::platform.hashing)
set_target_properties(${PROJECT_NAME} PROPERTIES CXX_STANDARD 20)
