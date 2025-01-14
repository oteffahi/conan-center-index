from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools import files, scm, build
from conan.tools.files import copy
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=1.52.0"


class PackioConan(ConanFile):
    name = "packio"
    description = "An asynchronous msgpack-RPC and JSON-RPC library built on top of Boost.Asio."
    license = "MPL-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/qchateau/packio"
    topics = ("rpc", "msgpack", "json", "asio", "async", "cpp17", "cpp20", "coroutines", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "standalone_asio": [True, False],
        "msgpack": [True, False],
        "nlohmann_json": [True, False],
        "boost_json": [True, False, "default"],
    }
    default_options = {
        "standalone_asio": False,
        "msgpack": True,
        "nlohmann_json": True,
        "boost_json": "default",
    }
    no_copy_source = True

    @property
    def _compilers_minimum_version(self):
        if scm.Version(self.version) < "2.4.0":
            return {"apple-clang": 10, "clang": 6, "gcc": 7, "Visual Studio": 16}
        return {"apple-clang": 13, "clang": 11, "gcc": 9, "Visual Studio": 16}

    def config_options(self):
        if scm.Version(self.version) < "1.2.0":
            self.options.rm_safe("standalone_asio")
        if scm.Version(self.version) < "2.0.0":
            self.options.rm_safe("msgpack")
            self.options.rm_safe("nlohmann_json")
        if scm.Version(self.version) < "2.1.0":
            self.options.rm_safe("boost_json")

    def configure(self):
        if self.settings.compiler.cppstd:
            build.check_min_cppstd(self, "17")

        minimum_version = self._compilers_minimum_version.get(str(self.settings.compiler), False)
        if minimum_version:
            if scm.Version(self.settings.compiler.version) < minimum_version:
                raise ConanInvalidConfiguration(
                    "packio requires C++17, which your compiler does not support."
                )
        else:
            self.output.warning(
                "packio requires C++17. Your compiler is unknown. Assuming it supports C++17."
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.get_safe("msgpack") or scm.Version(self.version) < "2.0.0":
            self.requires("msgpack/3.3.0")

        if self.options.get_safe("nlohmann_json"):
            self.requires("nlohmann_json/3.11.2")

        # defaults to True if using boost.asio, False if using asio
        if self.options.get_safe("boost_json") == "default":
            self.options.boost_json = not self.options.standalone_asio

        if self.options.get_safe("boost_json") or not self.options.get_safe("standalone_asio"):
            self.requires("boost/1.83.0")

        if self.options.get_safe("standalone_asio"):
            self.requires("asio/1.28.1")

    def package_id(self):
        self.info.clear()

    def source(self):
        files.get(conanfile=self, **self.conan_data["sources"][self.version])

    def package(self):
        copy(self, "LICENSE.md", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(self, "*.h",
             dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

        if scm.Version(self.version) < "2.1.0":
            if self.options.get_safe("standalone_asio"):
                self.cpp_info.defines.append("PACKIO_STANDALONE_ASIO")
        else:
            # Starting from 2.1.0, preprocessor defines can be defined to 0 to force-disable
            self.cpp_info.defines.append(
                f"PACKIO_STANDALONE_ASIO={1 if self.options.get_safe('standalone_asio') else 0}"
            )
            self.cpp_info.defines.append(f"PACKIO_HAS_MSGPACK={1 if self.options.get_safe('msgpack') else 0}")
            self.cpp_info.defines.append(
                f"PACKIO_HAS_NLOHMANN_JSON={1 if self.options.get_safe('nlohmann_json') else 0}"
            )
            self.cpp_info.defines.append(
                f"PACKIO_HAS_BOOST_JSON={1 if self.options.get_safe('boost_json') else 0}"
            )
