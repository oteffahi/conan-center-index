from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import export_conandata_patches, get
from conan.tools.scm import Version

required_conan_version = ">=1.53.0"


class ICCConan(ConanFile):
    name = "redradist-icc"
    description = (
        "I.C.C. - Inter Component Communication, This is a library created to simplify communication between "
        "components inside of single application. It is thread safe and could be used for creating "
        "components that works in different threads. "
    )
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/redradist/Inter-Component-Communication"
    topics = ("thread-safe", "active-object", "communication")

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

    @property
    def _minimum_cpp_standard(self):
        return 11

    @property
    def _minimum_compilers_version(self):
        return {
            "Visual Studio": "15",
            "msvc": "191",
            "apple-clang": "9.4",
            "clang": "3.3",
            "gcc": "4.9.4",
        }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.settings.get_safe("compiler.cppstd"):
            check_min_cppstd(self, self._minimum_cpp_standard)

        os = self.settings.os
        if os not in ("Windows", "Linux"):
            raise ConanInvalidConfiguration(f"OS {os} is not supported")

        compiler = self.settings.compiler
        try:
            min_version = self._minimum_compilers_version[str(compiler)]
            if Version(compiler.version) < min_version:
                raise ConanInvalidConfiguration(
                    f"{self.name} requires C++{self._minimum_cpp_standard} features "
                    f"which are not supported by compiler {compiler} {compiler.version}")
        except KeyError:
            self.output.warning(
                f"{self.name} recipe lacks information about the {compiler} compiler, "
                f"support for the required C++{self._minimum_cpp_standard} features is assumed"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ICC_BUILD_SHARED"] = self.options.shared
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "icc")
        self.cpp_info.set_property("cmake_target_name", "icc::icc")

        if self.options.shared:
            self.cpp_info.libs = ["ICC"]
        else:
            self.cpp_info.libs = ["ICC_static"]

        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32", "wsock32"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["pthread"]

        # TODO: to remove in conan v2 once cmake_find_package_* generators removed
        self.cpp_info.names["cmake_find_package"] = "icc"
        self.cpp_info.names["cmake_find_package_multi"] = "icc"
