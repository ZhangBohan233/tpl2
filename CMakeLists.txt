cmake_minimum_required(VERSION 3.15)
project(tpl2 C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_FLAGS_DEBUG -O2)

add_executable(tpl2 main.c tvm/tvm.c tvm/tvm.h tvm/util.c tvm/util.h tvm/os_spec.c tvm/os_spec.h)