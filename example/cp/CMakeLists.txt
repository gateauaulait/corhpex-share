cmake_minimum_required(VERSION 3.16)

project(PhysicBench
    VERSION 1.0
    DESCRIPTION "Benchmark of physical laws with different compile time and runtime configurations"
    LANGUAGES CXX)

# Custom build type NOFLAGS
set(CMAKE_C_FLAGS_NOFLAGS "" CACHE STRING "" FORCE)
set(CMAKE_CXX_FLAGS_NOFLAGS "" CACHE STRING "" FORCE)
set(CMAKE_EXE_LINKER_FLAGS_NOFLAGS "" CACHE STRING "" FORCE)
set(CMAKE_SHARED_LINKER_FLAGS_NOFLAGS "" CACHE STRING "" FORCE)
set(CMAKE_STATIC_LINKER_FLAGS_NOFLAGS "" CACHE STRING "" FORCE)
set(CMAKE_MODULE_LINKER_FLAGS_NOFLAGS "" CACHE STRING "" FORCE)

# Custom buid type OPTIMIZED (my custom flag mix)
set(CMAKE_C_FLAGS_OPTIMIZED "-march=native -funroll-all-loops -O3 -ffast-math" CACHE STRING "" FORCE)
set(CMAKE_CXX_FLAGS_OPTIMIZED "-march=native -funroll-all-loops -O3 -ffast-math" CACHE STRING "" FORCE)
set(CMAKE_EXE_LINKER_FLAGS_OPTIMIZED "-march=native -funroll-all-loops -O3 -ffast-math" CACHE STRING "" FORCE)
set(CMAKE_SHARED_LINKER_FLAGS_OPTIMIZED "-march=native -funroll-all-loops -O3 -ffast-math" CACHE STRING "" FORCE)
set(CMAKE_STATIC_LINKER_FLAGS_OPTIMIZED "" CACHE STRING "" FORCE)
set(CMAKE_MODULE_LINKER_FLAGS_OPTIMIZED "-march=native -funroll-all-loops -O3 -ffast-math" CACHE STRING "" FORCE)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

add_definitions(-DLIKWID_PERFMON)
add_definitions(-DLIKWID_PERFMON)
find_package(Threads REQUIRED)
link_libraries(Threads::Threads)
link_libraries(likwid)


find_package(OpenMP REQUIRED)
link_libraries(OpenMP::OpenMP_CXX)

add_library(cp
        CapillaryPressureLaw.cc)

add_executable(bench
        main.cc
        Benchmark.cc)

target_include_directories(bench PUBLIC .)

target_link_libraries(bench cp)
