cmake_minimum_required(VERSION 3.16)
project(wsjtx-log-univer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets)

# Parsing and merging logic (no Qt needed).
add_library(wsjtx_core STATIC src/adi.cpp src/unify.cpp)
target_include_directories(wsjtx_core PUBLIC src)

# The Qt6 desktop application.
add_executable(wsjtx_log_univer
    src/main.cpp
    src/log_window.cpp
    src/log_window.hpp
)
target_link_libraries(wsjtx_log_univer PRIVATE wsjtx_core Qt6::Widgets)

# Unit tests for the parsing/merging logic (reuses the sample log fixture).
add_executable(wsjtx_tests tests/test_wsjtx.cpp)
target_link_libraries(wsjtx_tests PRIVATE wsjtx_core)
target_compile_definitions(wsjtx_tests PRIVATE
    WSJTX_FIXTURE="${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/wsjtx_log.adi")

enable_testing()
add_test(NAME adi_tests COMMAND wsjtx_tests)

install(TARGETS wsjtx_log_univer RUNTIME DESTINATION bin)
