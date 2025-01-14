from conan import ConanFile
from conan.tools.cmake import cmake_layout, CMake
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_package = not cross_building(self.settings)
        if "x86" not in str(self.settings.arch).lower():
            test_package = False
        elif str(self.dependencies["llvm-core"].options.targets) not in ["all", "X86"]:
            test_package = False
        elif self.dependencies["llvm-core"].options.shared:
            if self.dependencies["llvm-core"].options.components != "all":
                requirements = ["interpreter", "irreader", "x86codegen"]
                targets = str(self.dependencies["llvm-core"].options.components)
                if self.settings.os == "Windows":
                    requirements.append("demangle")
                if not all([target in components for target in requirements]):
                    test_package = False

        if test_package:
            command = [
                os.path.join("bin", "test_package"),
                os.path.join(os.path.dirname(__file__), "test_function.ll"),
            ]
            self.run(command, run_environment=True)

        llvm_path = self.dependencies["llvm-core"].package_folder
        license_path = os.path.join(llvm_path, "licenses", "LICENSE.TXT")
        assert os.path.exists(license_path)
