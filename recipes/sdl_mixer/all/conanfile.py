import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy
from conan.tools.files import get, rmdir

required_conan_version = ">=1.53.0"


class SDLMixerConan(ConanFile):
    name = "sdl_mixer"
    description = "SDL_mixer is a sample multi-channel audio mixer library"
    license = "Zlib"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.libsdl.org/projects/SDL_mixer/"
    topics = ("sdl2", "sdl", "mixer", "audio", "multimedia", "sound", "music")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "cmd": [True, False],
        "wav": [True, False],
        "flac": [True, False],
        "mpg123": [True, False],
        "mad": [True, False],
        "ogg": [True, False],
        "opus": [True, False],
        "mikmod": [True, False],
        "modplug": [True, False],
        "fluidsynth": [True, False],
        "nativemidi": [True, False],
        "tinymidi": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "cmd": False,
        "wav": True,
        "flac": True,
        "mpg123": True,
        "mad": True,
        "ogg": True,
        "opus": True,
        "mikmod": True,
        "modplug": True,
        "fluidsynth": False,
        "nativemidi": True,
        "tinymidi": True,
    }

    def export_sources(self):
        copy(self, "CMakeLists.txt", src=self.recipe_folder, dst=self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os not in ["Linux", "FreeBSD"]:
            self.options.rm_safe("tinymidi")
        else:
            self.options.rm_safe("nativemidi")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("sdl/2.26.5", transitive_headers=True)
        if self.options.flac:
            self.requires("flac/1.4.2")
        if self.options.mpg123:
            self.requires("mpg123/1.31.2")
        if self.options.mad:
            self.requires("libmad/0.15.1b")
        if self.options.ogg:
            self.requires("ogg/1.3.5")
            self.requires("vorbis/1.3.7")
        if self.options.opus:
            self.requires("openssl/[>=1.1 <4]")
            self.requires("opus/1.4")
            self.requires("opusfile/0.12")
        if self.options.mikmod:
            self.requires("libmikmod/3.3.11.1")
        if self.options.modplug:
            self.requires("libmodplug/0.8.9.0")
        if self.options.fluidsynth:
            self.requires("fluidsynth/2.2")  # TODO: this package is missing on the conan-center-index
        if self.settings.os in ["Linux", "FreeBSD"]:
            if self.options.tinymidi:
                self.requires("tinymidi/cci.20130325")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        rmdir(self, os.path.join(self.source_folder, "external"))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMD"] = self.options.cmd
        tc.variables["WAV"] = self.options.wav
        tc.variables["FLAC"] = self.options.flac
        tc.variables["MP3_MPG123"] = self.options.mpg123
        tc.variables["MP3_MAD"] = self.options.mad
        tc.variables["OGG"] = self.options.ogg
        tc.variables["OPUS"] = self.options.opus
        tc.variables["MOD_MIKMOD"] = self.options.mikmod
        tc.variables["MOD_MODPLUG"] = self.options.modplug
        tc.variables["MID_FLUIDSYNTH"] = self.options.fluidsynth
        if self.settings.os in ["Linux", "FreeBSD"]:
            tc.variables["MID_TINYMIDI"] = self.options.tinymidi
            tc.variables["MID_NATIVE"] = False
        else:
            tc.variables["MID_TINYMIDI"] = False
            tc.variables["MID_NATIVE"] = self.options.nativemidi
        tc.variables["FLAC_DYNAMIC"] = self.dependencies["flac"].options.shared if self.options.flac else False
        tc.variables["MP3_MPG123_DYNAMIC"] = self.dependencies["mpg123"].options.shared if self.options.mpg123 else False
        tc.variables["OGG_DYNAMIC"] = self.dependencies["ogg"].options.shared if self.options.ogg else False
        tc.variables["OPUS_DYNAMIC"] = self.dependencies["opus"].options.shared if self.options.opus else False
        tc.variables["MOD_MIKMOD_DYNAMIC"] = self.dependencies["libmikmod"].options.shared if self.options.mikmod else False
        tc.variables["MOD_MODPLUG_DYNAMIC"] = self.dependencies["libmodplug"].options.shared if self.options.modplug else False
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.source_path.parent)
        cmake.build()

    def package(self):
        copy(self, "COPYING.txt",
            dst=os.path.join(self.package_folder, "licenses"),
            src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SDL2_mixer")
        self.cpp_info.set_property("cmake_target_name", "SDL2_mixer::SDL2_mixer")
        self.cpp_info.set_property("pkg_config_name", "SDL2_mixer")

        self.cpp_info.libs = ["SDL2_mixer"]
        self.cpp_info.includedirs.append(os.path.join("include", "SDL2"))
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]

        self.cpp_info.names["cmake_find_package"] = "SDL2_mixer"
        self.cpp_info.names["cmake_find_package_multi"] = "SDL2_mixer"
