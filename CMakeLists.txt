cmake_minimum_required(VERSION 3.20)
project(tpl2)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

add_executable(tpl2 main.c tvm/tvm.c tvm/tvm.h tvm/util.c tvm/util.h tvm/os_spec.c tvm/os_spec.h tvm/mem.c tvm/mem.h)
