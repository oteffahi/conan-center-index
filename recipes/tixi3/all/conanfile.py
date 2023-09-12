import os
import textwrap

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import export_conandata_patches, apply_conandata_patches, copy, get, rmdir, save

required_conan_version = ">=1.53.0"


class Tixi3Conan(ConanFile):
    name = "tixi3"
    description = "A simple xml interface based on libxml2 and libxslt"
    license = "Apache-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/DLR-SC/tixi"
    topics = ("xml", "xml2", "xslt")

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
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

        # tixi is a c library
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("libxml2/2.11.4")
        self.requires("libxslt/1.1.34")
        self.requires("libcurl/[>=7.78 <9]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["TIXI_BUILD_EXAMPLES"] = False
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _create_cmake_module_alias_targets(self, module_file, targets):
        content = ""
        for alias, aliased in targets.items():
            content += textwrap.dedent(f"""\
                if(TARGET {aliased} AND NOT TARGET {alias})
                    add_library({alias} INTERFACE IMPORTED)
                    set_property(TARGET {alias} PROPERTY INTERFACE_LINK_LIBRARIES {aliased})
                endif()
            """)
        save(self, module_file, content)

    def package(self):
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "tixi3"))
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        rmdir(self, os.path.join(self.package_folder, "share"))

        # provide alias target tixi3 for v1 packages
        self._create_cmake_module_alias_targets(
            os.path.join(self.package_folder, self._module_file_rel_path), {"tixi3": "tixi3::tixi3"}
        )

    @property
    def _module_file_rel_path(self):
        return os.path.join("lib", "cmake", "conan-official-{}-targets.cmake".format(self.name))

    def package_info(self):
        self.cpp_info.includedirs.append(os.path.join("include", "tixi3"))

        if self.settings.build_type != "Debug":
            self.cpp_info.libs = ["tixi3"]
        else:
            self.cpp_info.libs = ["tixi3-d"]

        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["shlwapi"]

        self.cpp_info.frameworks.extend(["Foundation"])

        self.cpp_info.set_property("cmake_file_name", "tixi3")
        self.cpp_info.set_property("cmake_target_name", "tixi3")

        # provide alias target tixi3 for v1 packages
        self.cpp_info.builddirs.append(os.path.join("lib", "cmake"))
        self.cpp_info.build_modules["cmake_find_package"] = [self._module_file_rel_path]
        self.cpp_info.build_modules["cmake_find_package_multi"] = [self._module_file_rel_path]
