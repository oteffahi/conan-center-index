import os
import shutil
from contextlib import contextmanager

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "a.cpp", "b.cpp", "main.c", "main.cpp", "wscript"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        if not can_run(self):
            return

        for src in self.exports_sources:
            shutil.copy(os.path.join(self.source_folder, src), self.build_folder)

        waf_path = which(self, "waf")
        if waf_path:
            waf_path = waf_path.replace("\\", "/")
            assert waf_path.startswith(str(self.deps_cpp_info["waf"].rootpath))

        with vcvars(self.settings) if self.settings.compiler == "Visual Studio" else no_op(
            self,
        ):
            self.run("waf -h")
            self.run("waf configure")
            self.run("waf")

    @contextmanager
    def _add_ld_search_path(self):
        env = {}
        if self.settings.os == "Linux":
            env["LD_LIBRARY_PATH"] = [os.path.join(os.getcwd(), "build")]
        elif self.settings.os == "Macos":
            env["DYLD_LIBRARY_PATH"] = [os.path.join(os.getcwd(), "build")]
        with environment_append(self, env):
            yield

    def test(self):
        if can_run(self):
            with self._add_ld_search_path():
                bin_path = os.path.join(self.cpp.build.bindir, "app")
                self.run(bin_path, env="conanrun")
                bin_path = os.path.join(self.cpp.build.bindir, "app2")
                self.run(bin_path, env="conanrun")
