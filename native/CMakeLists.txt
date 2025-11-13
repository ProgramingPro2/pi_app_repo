cmake_minimum_required(VERSION 3.16)
project(seekshim LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenCV REQUIRED)

# Try to find libseek in various possible locations
# Case 1: pi_app_repo is inside libseek-thermal (../../build/src)
# Case 2: pi_app_repo is sibling to libseek-thermal (../../../libseek-thermal/build/src)
# Case 3: System installation

# First, try to find the library file directly
# CMAKE_CURRENT_SOURCE_DIR is native/ (where this CMakeLists.txt is)
# Case 1: pi_app_repo is inside libseek-thermal: ../../build/src
# Case 2: pi_app_repo is sibling to libseek-thermal: ../../libseek-thermal/build/src
set(SEEK_LIBRARY "")
set(PATH1 "${CMAKE_CURRENT_SOURCE_DIR}/../../build/src/libseek.so")
set(PATH2 "${CMAKE_CURRENT_SOURCE_DIR}/../../libseek-thermal/build/src/libseek.so")
get_filename_component(PATH1_ABS "${PATH1}" ABSOLUTE)
get_filename_component(PATH2_ABS "${PATH2}" ABSOLUTE)

if(EXISTS "${PATH1_ABS}")
    set(SEEK_LIBRARY "${PATH1_ABS}")
    message(STATUS "Found libseek.so at: ${SEEK_LIBRARY}")
elseif(EXISTS "${PATH2_ABS}")
    set(SEEK_LIBRARY "${PATH2_ABS}")
    message(STATUS "Found libseek.so at: ${SEEK_LIBRARY}")
else()
    # Try system paths
    find_library(SEEK_LIBRARY seek
        PATHS
            /usr/local/lib
            /usr/lib
        NO_DEFAULT_PATH
    )
    
    # If still not found, try default system paths
    if(NOT SEEK_LIBRARY)
        find_library(SEEK_LIBRARY seek REQUIRED)
    endif()
endif()

if(NOT SEEK_LIBRARY)
    message(FATAL_ERROR "Could not find libseek.so. Please build libseek first or install it system-wide.")
endif()

# Find header files - try local build first, then system paths
set(SEEK_INCLUDE_DIRS "")
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../../src")
    list(APPEND SEEK_INCLUDE_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/../../src")
endif()
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../../libseek-thermal/src")
    list(APPEND SEEK_INCLUDE_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/../../libseek-thermal/src")
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
# Try both possible locations
set(SEEK_LIB_DIR "")
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../../build/src/libseek.so")
    set(SEEK_LIB_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../build/src")
elseif(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../../libseek-thermal/build/src/libseek.so")
    set(SEEK_LIB_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../libseek-thermal/build/src")
endif()

if(SEEK_LIB_DIR)
    set_target_properties(seekshim PROPERTIES
        BUILD_RPATH "${SEEK_LIB_DIR}"
        INSTALL_RPATH "${SEEK_LIB_DIR}"
    )
endif()

