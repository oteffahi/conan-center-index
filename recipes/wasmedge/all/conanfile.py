# Warnings:
#   Unexpected method '_compiler_alias'
#   Missing required method 'generate'
#   Missing required method 'build'

from conan import ConanFile
from conan.tools.files import get, copy, download
from conan.tools.scm import Version
from conan.errors import ConanInvalidConfiguration

import os

required_conan_version = ">=1.53.0"


class WasmedgeConan(ConanFile):
    name = "wasmedge"
    description = (
        "WasmEdge is a lightweight, high-performance, and extensible WebAssembly runtime for cloud native,"
        " edge, and decentralized applications. "
        "It powers serverless apps, embedded functions, microservices, smart contracts, and IoT devices."
    )
    license = "Apache-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/WasmEdge/WasmEdge/"
    topics = ("webassembly", "wasm", "wasi", "emscripten", "pre-built")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    @property
    def _compiler_alias(self):
        return {
            "Visual Studio": "Visual Studio",
            "msvc": "Visual Studio",
        }.get(str(self.settings.compiler), "gcc")

    def configure(self):
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        pass

    def package_id(self):
        del self.info.settings.compiler.version
        self.info.settings.compiler = self._compiler_alias

    @property
    def _data(self):
        version_info = self.conan_data["sources"][self.version]
        return version_info[str(self.settings.os)][str(self.settings.arch)][self._compiler_alias]

    def validate(self):
        try:
            self._data
        except KeyError:
            raise ConanInvalidConfiguration(
                "Binaries for this combination of version/os/arch/compiler are not available"
            )

    def source(self):
        # This is packaging binaries so the download needs to be in build
        binaries_info, license_info = self._data
        get(self, **binaries_info, strip_root=True)
        download(self, **license_info, filename="LICENSE")

    def package(self):
        copy(self, "*.h",
             dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "include"))
        copy(self, "*.inc",
             dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "include"))

        srclibdir = os.path.join(self.source_folder, "lib64" if self.settings.os in ["Linux", "FreeBSD"] else "lib")
        srcbindir = os.path.join(self.source_folder, "bin")
        dstlibdir = os.path.join(self.package_folder, "lib")
        dstbindir = os.path.join(self.package_folder, "bin")
        if Version(self.version) >= "0.11.1":
            copy(self, "wasmedge.lib",
                 src=srclibdir,
                 dst=dstlibdir,
                 keep_path=False)
            copy(self, "wasmedge.dll",
                 src=srcbindir,
                 dst=dstbindir,
                 keep_path=False)
            copy(self, "libwasmedge.so*",
                 src=srclibdir,
                 dst=dstlibdir,
                 keep_path=False)
            copy(self, "libwasmedge*.dylib",
                 src=srclibdir,
                 dst=dstlibdir,
                 keep_path=False)
        else:
            copy(self, "wasmedge_c.lib",
                 src=srclibdir,
                 dst=dstlibdir,
                 keep_path=False)
            copy(self, "wasmedge_c.dll",
                 src=srcbindir,
                 dst=dstbindir,
                 keep_path=False)
            copy(self, "libwasmedge_c.so*",
                 src=srclibdir,
                 dst=dstlibdir,
                 keep_path=False)
            copy(self, "libwasmedge_c*.dylib",
                 src=srclibdir,
                 dst=dstlibdir,
                 keep_path=False)

        copy(self, "wasmedge*",
             src=srcbindir,
             dst=dstbindir,
             keep_path=False)
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        if Version(self.version) >= "0.11.1":
            self.cpp_info.libs = ["wasmedge"]
        else:
            self.cpp_info.libs = ["wasmedge_c"]

        bindir = os.path.join(self.package_folder, "bin")
        self.output.info("Appending PATH environment variable: {}".format(bindir))
        self.env_info.PATH.append(bindir)

        if self.settings.os == "Windows":
            self.cpp_info.system_libs.append("ws2_32")
            self.cpp_info.system_libs.append("wsock32")
            self.cpp_info.system_libs.append("shlwapi")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
            self.cpp_info.system_libs.append("dl")
            self.cpp_info.system_libs.append("rt")
            self.cpp_info.system_libs.append("pthread")
