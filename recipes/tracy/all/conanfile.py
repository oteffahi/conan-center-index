from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir
from conan.tools.scm import Version
import os

required_conan_version = ">=1.53.0"


class TracyConan(ConanFile):
    name = "tracy"
    description = "C++ frame profiler"
    license = ["BSD-3-Clause"]
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/wolfpld/tracy"
    topics = ("profiler", "performance", "gamedev")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"

    # Existing CMake tracy options with default value
    _tracy_options = {
        "enable": ([True, False], True),
        "on_demand": ([True, False], False),
        "callstack": ([True, False], False),
        "no_callstack": ([True, False], False),
        "no_callstack_inlines": ([True, False], False),
        "only_localhost": ([True, False], False),
        "no_broadcast": ([True, False], False),
        "only_ipv4": ([True, False], False),
        "no_code_transfer": ([True, False], False),
        "no_context_switch": ([True, False], False),
        "no_exit": ([True, False], False),
        "no_sampling": ([True, False], False),
        "no_verify": ([True, False], False),
        "no_vsync_capture": ([True, False], False),
        "no_frame_image": ([True, False], False),
        "no_system_tracing": ([True, False], False),
        "delayed_init": ([True, False], False),
        "manual_lifetime": ([True, False], False),
        "fibers": ([True, False], False),
        "no_crash_handler": ([True, False], False),
        "timer_fallback": ([True, False], False),
    }
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable": [True, False],
        "on_demand": [True, False],
        "callstack": [True, False],
        "no_callstack": [True, False],
        "no_callstack_inlines": [True, False],
        "only_localhost": [True, False],
        "no_broadcast": [True, False],
        "only_ipv": [True, False],
        "no_code_transfer": [True, False],
        "no_context_switch": [True, False],
        "no_exit": [True, False],
        "no_sampling": [True, False],
        "no_verify": [True, False],
        "no_vsync_capture": [True, False],
        "no_frame_image": [True, False],
        "no_system_tracing": [True, False],
        "delayed_init": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable": True,
        "on_demand": False,
        "callstack": False,
        "no_callstack": False,
        "no_callstack_inlines": False,
        "only_localhost": False,
        "no_broadcast": False,
        "only_ipv": False,
        "no_code_transfer": False,
        "no_context_switch": False,
        "no_exit": False,
        "no_sampling": False,
        "no_verify": False,
        "no_vsync_capture": False,
        "no_frame_image": False,
        "no_system_tracing": False,
        "delayed_init": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

        if Version(self.version) < "0.9":
            self.options.rm_safe("manual_lifetime")
            self.options.rm_safe("fibers")
            self.options.rm_safe("no_crash_handler")
            self.options.rm_safe("timer_fallback")

            del self._tracy_options["manual_lifetime"]
            del self._tracy_options["fibers"]
            del self._tracy_options["no_crash_handler"]
            del self._tracy_options["timer_fallback"]

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.info.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @property
    def _tracy_options(self):
        return [opt for opt in self.options if opt not in ["shared", "fPIC"]]

    def generate(self):
        tc = CMakeToolchain(self)
        # Set all tracy options in the correct form
        # For example, TRACY_NO_EXIT
        for opt in self._tracy_options:
            switch = getattr(self.options, opt)
            opt = f"TRACY_{opt.upper()}"
            tc.variables[opt] = switch
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Tracy")
        self.cpp_info.set_property("cmake_target_name", "Tracy::TracyClient")
        # TODO: back to global scope in conan v2
        self.cpp_info.components["tracyclient"].libs = ["TracyClient"]
        if self.options.shared:
            self.cpp_info.components["tracyclient"].defines.append("TRACY_IMPORTS")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["tracyclient"].system_libs.append("pthread")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["tracyclient"].system_libs.append("dl")

        # Tracy CMake adds options set to ON as public
        for opt in self._tracy_options:
            switch = getattr(self.options, opt)
            opt = f"TRACY_{opt.upper()}"
            if switch:
                self.cpp_info.components["tracyclient"].defines.append(opt)

        # TODO: to remove in conan v2
        self.cpp_info.names["cmake_find_package"] = "Tracy"
        self.cpp_info.names["cmake_find_package_multi"] = "Tracy"
        self.cpp_info.components["tracyclient"].names["cmake_find_package"] = "TracyClient"
        self.cpp_info.components["tracyclient"].names["cmake_find_package_multi"] = "TracyClient"
        self.cpp_info.components["tracyclient"].set_property("cmake_target_name", "Tracy::TracyClient")
