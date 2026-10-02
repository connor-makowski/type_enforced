cmake_minimum_required(VERSION 3.15)

# -----------------------------
# Define The Project
# -----------------------------
project(type_enforced LANGUAGES CXX)

# -----------------------------
# Find Packages
# -----------------------------
find_package(Python 3.10 REQUIRED COMPONENTS Interpreter Development.Module)
find_package(nanobind CONFIG REQUIRED)

# -----------------------------
# Set C++ standard
# -----------------------------
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# -----------------------------
# OPTIMIZATION FLAGS
# -----------------------------
set(CMAKE_BUILD_TYPE Release)
if(MSVC)
    set(CMAKE_CXX_FLAGS_RELEASE "/O2 /DNDEBUG")
else()
    set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")
endif()

# -----------------------------
# type_enforced module
# -----------------------------
nanobind_add_module(cpp
    STABLE_ABI
    type_enforced/cpp/bindings/type_enforced_bindings.cpp
    type_enforced/cpp/src/validators.cpp
)

install(TARGETS cpp DESTINATION type_enforced)

# -----------------------------
# Install Python package files
# -----------------------------
install(DIRECTORY type_enforced DESTINATION . FILES_MATCHING PATTERN "*.py")
