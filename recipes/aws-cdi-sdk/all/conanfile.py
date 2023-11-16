import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir

required_conan_version = ">=1.53.0"


class AwsCdiSdkConan(ConanFile):
    name = "aws-cdi-sdk"
    description = "AWS Cloud Digital Interface (CDI) SDK"
    license = "BSD-2-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/aws/aws-cdi-sdk"
    topics = ("aws", "communication", "framework", "service")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.options["aws-libfabric"].shared = True
        self.options["aws-sdk-cpp"].shared = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("aws-libfabric/1.9.1amzncdi1.0")
        self.requires("aws-sdk-cpp/1.9.234")

    def validate(self):
        if not self.dependencies["aws-libfabric"].options.shared or not self.dependencies["aws-sdk-cpp"].options.shared:
            raise ConanInvalidConfiguration("Cannot build with static dependencies")
        if not self.dependencies["aws-sdk-cpp"].options.get_safe("monitoring"):
            raise ConanInvalidConfiguration("This package requires the monitoring AWS SDK")
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # https://github.com/aws/aws-cdi-sdk/blob/v2.4.1/Makefile#L23-L34
        # https://github.com/aws/aws-cdi-sdk/blob/v2.4.1/include/cdi_core_api.h#L67-L74
        product, major, minor = self.version.split(".")[:3]
        tc.variables["PRODUCT_VERSION"] = product
        tc.variables["MAJOR_MINOR_VERSION"] = f"{major}.{minor}"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "aws-cdi-sdk")
        self.cpp_info.set_property("cmake_target_aliases", ["aws-cdi-sdk"])

        cppSdk = self.cpp_info.components["aws-cpp-sdk-cdi"]
        cppSdk.set_property("cmake_target_name", "AWS::aws-cpp-sdk-cdi")
        cppSdk.set_property("pkg_config_name", "aws-cpp-sdk-cdi")
        cppSdk.libs = ["aws-cpp-sdk-cdi"]
        cppSdk.requires = ["aws-sdk-cpp::monitoring", "aws-libfabric::aws-libfabric"]

        cSdk = self.cpp_info.components["cdisdk"]
        cSdk.set_property("cmake_target_name", "AWS::aws-cdi-sdk")
        cSdk.set_property("pkg_config_name", "aws-cdi-sdk")
        cSdk.libs = ["cdisdk"]
        cSdk.requires = ["aws-cpp-sdk-cdi"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            cSdk.defines = ["_LINUX"]

        # TODO: to remove in conan v2 once cmake_find_package_* generators removed
        # TODO: Remove the namespace on CMake targets
        self.cpp_info.names["cmake_find_package"] = "AWS"
        self.cpp_info.names["cmake_find_package_multi"] = "AWS"
        self.cpp_info.filenames["cmake_find_package"] = "aws-cdi-sdk"
        self.cpp_info.filenames["cmake_find_package_multi"] = "aws-cdi-sdk"
        cppSdk.names["cmake_find_package"] = "aws-cpp-sdk-cdi"
        cppSdk.names["cmake_find_package_multi"] = "aws-cpp-sdk-cdi"
        cSdk.names["cmake_find_package"] = "aws-cdi-sdk"
        cSdk.names["cmake_find_package_multi"] = "aws-cdi-sdk"
