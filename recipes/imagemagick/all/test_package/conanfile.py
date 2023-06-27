from conan import ConanFile
from conan.tools.build import can_run
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
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")

            with open("delegates.txt") as f:
                content = f.read()

                def check(option, token):
                    self.output.info("checking feature %s..." % token)
                    if option:
                        if token not in content.split():
                            raise Exception("feature %s wasn't enabled!" % token)
                    self.output.info("checking feature %s... OK!" % token)

                check(self.options["imagemagick"].with_zlib, "zlib")
                check(self.options["imagemagick"].with_bzlib, "bzlib")
                check(self.options["imagemagick"].with_lzma, "lzma")
                check(self.options["imagemagick"].with_lcms, "lcms")
                check(self.options["imagemagick"].with_openexr, "openexr")
                check(self.options["imagemagick"].with_heic, "heic")
                check(self.options["imagemagick"].with_jbig, "jbig")
                check(self.options["imagemagick"].with_jpeg, "jpeg")
                check(self.options["imagemagick"].with_openjp2, "jp2")
                check(self.options["imagemagick"].with_pango, "pangocairo")
                check(self.options["imagemagick"].with_png, "png")
                check(self.options["imagemagick"].with_tiff, "tiff")
                check(self.options["imagemagick"].with_webp, "webp")
                check(self.options["imagemagick"].with_freetype, "freetype")
                check(self.options["imagemagick"].with_xml2, "xml")
