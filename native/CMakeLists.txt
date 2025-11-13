cmake_minimum_required(VERSION 3.16)
project(seekshim LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenCV REQUIRED)

# Try to find libseek in system paths first, then fall back to local build
find_library(SEEK_LIBRARY seek
    PATHS
        ${CMAKE_SOURCE_DIR}/../../build/src
        /usr/local/lib
        /usr/lib
    NO_DEFAULT_PATH
)

# If not found, try default system paths
if(NOT SEEK_LIBRARY)
    find_library(SEEK_LIBRARY seek REQUIRED)
endif()

# Find header files - try local build first, then system paths
set(SEEK_INCLUDE_DIRS "")
if(EXISTS "${CMAKE_SOURCE_DIR}/../../src")
    list(APPEND SEEK_INCLUDE_DIRS "${CMAKE_SOURCE_DIR}/../../src")
endif()
if(EXISTS "/usr/local/include/seek")
    list(APPEND SEEK_INCLUDE_DIRS "/usr/local/include/seek")
endif()

add_library(seekshim SHARED seek_wrapper.cpp)
target_include_directories(seekshim
    PRIVATE
        ${OpenCV_INCLUDE_DIRS}
        ${SEEK_INCLUDE_DIRS}
)
target_link_libraries(seekshim
    PRIVATE
        ${SEEK_LIBRARY}
        ${OpenCV_LIBS}
)

# Set RPATH so libseekshim.so can find libseek.so at runtime
if(EXISTS "${CMAKE_SOURCE_DIR}/../../build/src/libseek.so")
    set_target_properties(seekshim PROPERTIES
        BUILD_RPATH "${CMAKE_SOURCE_DIR}/../../build/src"
        INSTALL_RPATH "${CMAKE_SOURCE_DIR}/../../build/src"
    )
endif()

