cmake_minimum_required(VERSION 3.12)
project(strmbas)

set(DSROOT "${CMAKE_CURRENT_SOURCE_DIR}/src/Samples/Win7Samples/multimedia/directshow/baseclasses")

file(GLOB SOURCES "${DSROOT}/*.cpp")
file(GLOB HEADERS "${DSROOT}/*.h")

add_library(${PROJECT_NAME} STATIC ${SOURCES} ${HEADERS})

set_target_properties(${PROJECT_NAME} PROPERTIES
  PUBLIC_HEADER "${HEADERS}"
  DEBUG_POSTFIX d
  RELEASE_POSTFIX e)

target_include_directories(${PROJECT_NAME} PRIVATE ${DSROOT})

target_compile_definitions(${PROJECT_NAME} PRIVATE UNICODE=1 _UNICODE=1)

include(GNUInstallDirs)
install(TARGETS ${PROJECT_NAME}
  PUBLIC_HEADER DESTINATION include)
