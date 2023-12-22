#!/usr/bin/env python
# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A script to convert Bazel build systems to CMakeLists.txt.

See README.md for more information.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from collections.abc import Mapping
from argparse import ArgumentParser
import os

import sys
import textwrap

path_prefix=""
strip_prefixes=[]
skip_targets=[]
Trans_Func=None
def is_c_cplusplus_file(name):
    return name.endswith(".c") or name.endswith(".cc") or name.endswith(".h") or name.endswith(".cpp") or name.endswith(".hpp") or name.endswith(".s") or name.endswith(".S")
def path_map(name):
    if len(path_prefix)>0 and is_c_cplusplus_file(name):
       return os.path.join(path_prefix,name) 
    else:
       return name
def StripColons(deps):
    return map(lambda x: x[1:] if x[0]==':' else x, deps)
def Strip_Prefix(deps):
    for ss in strip_prefixes:
        deps=map(lambda x: x[x.startswith(ss) and len(ss):],deps)
    return deps

def IsSourceFile(name):
  return name.endswith(".c") or name.endswith(".cc")

class BuildFileFunctions(Mapping):
  def __init__(self, converter):
    self.converter = converter
    self.kv={}
  def __len__(self):
    return 1
  def __getitem__(self,k):
    v=getattr(self,k,None)
    if v!=None:
        return v
    if k in self.kv:
     return self.kv[k]
    else:
     def ff(*arg,**kargs):
         pass
     return ff
  def __setitem__(self,k,v):
     self.kv[k]=v
  def __iter__(self):
     return iter([])

  def _add_deps(self, kwargs, keyword=""):
    if "deps" not in kwargs:
      return
    deps=StripColons(kwargs["deps"])
    deps=Strip_Prefix(deps)
    if Trans_Func !=None:
        deps=Trans_Func(deps)
    self.converter.toplevel += "target_link_libraries(%s%s\n  %s)\n" % (
        kwargs["name"],
        keyword,
        "\n  ".join(deps)
    )

  def load(self, *args):
    pass

  def cc_library(self, **kwargs):
    if kwargs["name"] == "amalgamation" or kwargs["name"] == "upbc_generator":
      return
    if kwargs["name"] in skip_targets:
      return
    files = kwargs.get("srcs", []) + kwargs.get("hdrs", [])
    files=map(path_map,files)
    if filter(IsSourceFile, files):
      # Has sources, make this a normal library.
      self.converter.toplevel += "add_library(%s\n  %s)\n" % (
          kwargs["name"],
          "\n  ".join(files)
      )
      self._add_deps(kwargs)
    else:
      # Header-only library, have to do a couple things differently.
      # For some info, see:
      #  http://mariobadr.com/creating-a-header-only-library-with-cmake.html
      self.converter.toplevel += "add_library(%s INTERFACE)\n" % (
          kwargs["name"]
      )
      self._add_deps(kwargs, " INTERFACE")

  def cc_binary(self, **kwargs):
    pass

  def cc_test(self, **kwargs):
    # Disable this until we properly support upb_proto_library().
    # self.converter.toplevel += "add_executable(%s\n  %s)\n" % (
    #     kwargs["name"],
    #     "\n  ".join(kwargs["srcs"])
    # )
    # self.converter.toplevel += "add_test(NAME %s COMMAND %s)\n" % (
    #     kwargs["name"],
    #     kwargs["name"],
    # )

    # if "data" in kwargs:
    #   for data_dep in kwargs["data"]:
    #     self.converter.toplevel += textwrap.dedent("""\
    #       add_custom_command(
    #           TARGET %s POST_BUILD
    #           COMMAND ${CMAKE_COMMAND} -E copy
    #                   ${CMAKE_SOURCE_DIR}/%s
    #                   ${CMAKE_CURRENT_BINARY_DIR}/%s)\n""" % (
    #       kwargs["name"], data_dep, data_dep
    #     ))

    # self._add_deps(kwargs)
    pass

  def py_library(self, **kwargs):
    pass

  def py_binary(self, **kwargs):
    pass

  def lua_cclibrary(self, **kwargs):
    pass

  def lua_library(self, **kwargs):
    pass

  def lua_binary(self, **kwargs):
    pass

  def lua_test(self, **kwargs):
    pass

  def sh_test(self, **kwargs):
    pass

  def make_shell_script(self, **kwargs):
    pass

  def exports_files(self, files, **kwargs):
    pass

  def proto_library(self, **kwargs):
    pass

  def generated_file_staleness_test(self, **kwargs):
    pass

  def upb_amalgamation(self, **kwargs):
    pass

  def upb_proto_library(self, **kwargs):
    pass

  def upb_proto_reflection_library(self, **kwargs):
    pass

  def genrule(self, **kwargs):
    pass

  def config_setting(self, **kwargs):
    pass

  def select(self, arg_dict):
    return []

  def glob(self, *args):
    return []

  def licenses(self, *args):
    pass

  def map_dep(self, arg):
    return arg


class WorkspaceFileFunctions(object):
  def __init__(self, converter):
    self.converter = converter

  def load(self, *args):
    pass

  def workspace(self, **kwargs):
    self.converter.prelude += "project(%s)\n" % (kwargs["name"])

  def http_archive(self, **kwargs):
    pass

  def git_repository(self, **kwargs):
    pass


class Converter(object):
  def __init__(self):
    self.prelude = ""
    self.toplevel = ""
    self.if_lua = ""
    self.project=""

  def convert(self):
    return self.template % {
        "prelude": converter.prelude,
        "toplevel": converter.toplevel,
    }

  template = textwrap.dedent("""\
    # This file was generated from BUILD using tools/make_cmakelists.py.

    cmake_minimum_required(VERSION 3.1)
    %(project)s

    %(prelude)s

    # Prevent CMake from setting -rdynamic on Linux (!!).
    SET(CMAKE_SHARED_LIBRARY_LINK_C_FLAGS "")
    SET(CMAKE_SHARED_LIBRARY_LINK_CXX_FLAGS "")

    # Set default build type.
    if(NOT CMAKE_BUILD_TYPE)
      message(STATUS "Setting build type to 'RelWithDebInfo' as none was specified.")
      set(CMAKE_BUILD_TYPE "RelWithDebInfo" CACHE STRING
          "Choose the type of build, options are: Debug Release RelWithDebInfo MinSizeRel."
          FORCE)
    endif()

    # When using Ninja, compiler output won't be colorized without this.
    include(CheckCXXCompilerFlag)
    CHECK_CXX_COMPILER_FLAG(-fdiagnostics-color=always SUPPORTS_COLOR_ALWAYS)
    if(SUPPORTS_COLOR_ALWAYS)
      set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fdiagnostics-color=always")
    endif()

    # Implement ASAN/UBSAN options
    if(UPB_ENABLE_ASAN)
      set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fsanitize=address")
      set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fsanitize=address")
      set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -fsanitize=address")
      set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -fsanitize=address")
    endif()

    if(UPB_ENABLE_UBSAN)
      set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fsanitize=undefined")
      set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fsanitize=address")
      set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -fsanitize=address")
      set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -fsanitize=address")
    endif()

    include_directories(.)
    include_directories(${CMAKE_CURRENT_BINARY_DIR})

    if(APPLE)
      set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -undefined dynamic_lookup -flat_namespace")
    elseif(UNIX)
      set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -Wl,--build-id")
    endif()

    enable_testing()

    %(toplevel)s

  """)

data = {}
converter = Converter()

def GetDict(obj):
  ret = {}
  for k in dir(obj):
    if not k.startswith("_"):
      ret[k] = getattr(obj, k);
  return ret

globs = GetDict(converter)
dummy=BuildFileFunctions(converter)
default_output="CMakeLists.txt"
parser = ArgumentParser(prog="bazel2cmake",description='bazel to cmake converter')
parser.add_argument("files",nargs='+')
parser.add_argument("-s","--strip",nargs='*',help="strip prefix")
parser.add_argument("-p","--project",default="",help="project name")
parser.add_argument("-i","--ignore",nargs='*',default=skip_targets,help="ignore bazel target")
parser.add_argument("-t","--trans",default="",help="trans python filename")
parser.add_argument("-o","--output",default=default_output,help="cmake output default to CMakeLists.txt")
#exec(open("internal/BUILD").read(),GetDict(dummy),dummy)
#exec(open("BUILD").read(),GetDict(dummy),dummy)
#execfile("WORKSPACE", GetDict(WorkspaceFileFunctions(converter)))
#execfile("BUILD", GetDict(BuildFileFunctions(converter)))
args=parser.parse_args()
default_output=args.output
strip_prefixes =args.strip
trans_filename=args.trans;
skip_targets=args.ignore

if len(trans_filename)>0 and os.path.isfile(trans_filename) and trans_filename.endswith(".py"):
    trans_filename=trans_filename[:len(trans_filename)-3]
    trans_m=__import__(trans_filename)
    Trans_Func=getattr(trans_m,"trans",None)

for fname in args.files:
    if not os.path.isfile(fname):
        print(f"File {fname} doesn't exist!")
        continue
    path_prefix=os.path.dirname(fname)
    exec(open(fname).read(),GetDict(dummy),dummy)
with open(default_output, "w") as f:
  f.write(converter.convert())