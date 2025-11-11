cmake_minimum_required(VERSION 3.16)
project(seekshim LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenCV REQUIRED)

find_library(SEEK_LIBRARY seek REQUIRED)

add_library(seekshim SHARED seek_wrapper.cpp)
target_include_directories(seekshim
    PRIVATE
        ${OpenCV_INCLUDE_DIRS}
        ${CMAKE_SOURCE_DIR}/../../src
        /usr/local/include/seek
)
target_link_libraries(seekshim
    PRIVATE
        ${SEEK_LIBRARY}
        ${OpenCV_LIBS}
)

