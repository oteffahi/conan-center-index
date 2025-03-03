# TODO: verify the Conan v2 migration

import os
from contextlib import nullcontext

from conan import ConanFile, conan_version
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.android import android_abi
from conan.tools.apple import (
    XCRun,
    fix_apple_shared_install_name,
    is_apple_os,
    to_apple_arch,
)
from conan.tools.build import (
    build_jobs,
    can_run,
    check_min_cppstd,
    cross_building,
    default_cppstd,
    stdcpp_library,
    valid_min_cppstd,
)
from conan.tools.cmake import (
    CMake,
    CMakeDeps,
    CMakeToolchain,
    cmake_layout,
)
from conan.tools.env import (
    Environment,
    VirtualBuildEnv,
    VirtualRunEnv,
)
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    collect_libs,
    copy,
    download,
    export_conandata_patches,
    get,
    load,
    mkdir,
    patch,
    patches,
    rename,
    replace_in_file,
    rm,
    rmdir,
    save,
    symlinks,
    unzip,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfig,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain, Meson
from conan.tools.microsoft import (
    MSBuild,
    MSBuildDeps,
    MSBuildToolchain,
    NMakeDeps,
    NMakeToolchain,
    VCVars,
    check_min_vs,
    is_msvc,
    is_msvc_static_runtime,
    msvc_runtime_flag,
    unix_path,
    unix_path_package_info_legacy,
    vs_layout,
)
from conan.tools.scm import Version
from conan.tools.system import package_manager
from conan.tools.microsoft import msvc_runtime_flag
import glob
import os
import shutil

required_conan_version = ">=1.53.0"


class GStPluginsBadConan(ConanFile):
    name = "gst-plugins-bad"
    description = (
        "GStreamer is a development framework for creating applications like media players, video editors,"
        " streaming media broadcasters and so on"
    )
    license = "GPL-2.0-only"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://gstreamer.freedesktop.org/"
    topics = ("gstreamer", "multimedia", "video", "audio", "broadcasting", "framework", "media")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_introspection": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_introspection": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")
        self.options["gstreamer"].shared = self.options.shared
        self.options["gst-plugins-base"].shared = self.options.shared

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/2.78.0")
        self.requires("gstreamer/1.22.3")
        self.requires("gst-plugins-base/1.19.2")

    def validate(self):
        if (
            self.options.shared != self.dependencies["gstreamer"].options.shared
            or self.options.shared != self.dependencies["glib"].options.shared
            or self.options.shared != self.dependencies["gst-plugins-base"].options.shared
        ):
            # https://gitlab.freedesktop.org/gstreamer/gst-build/-/issues/133
            raise ConanInvalidConfiguration(
                "GLib, GStreamer and GstPlugins must be either all shared, or all static"
            )
        if (
            Version(self.version) >= "1.18.2"
            and self.settings.compiler == "gcc"
            and Version(self.settings.compiler.version) < "5"
        ):
            raise ConanInvalidConfiguration(
                "gst-plugins-bad %s does not support gcc older than 5" % self.version
            )
        if self.options.shared and is_msvc_static_runtime(self):
            raise ConanInvalidConfiguration(
                "shared build with static runtime is not supported due to the FlsAlloc limit"
            )

    def build_requirements(self):
        self.tool_requires("meson/1.2.1")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/2.0.3")
        if self.settings.os == "Windows":
            self.tool_requires("winflexbison/2.5.24")
        else:
            self.tool_requires("bison/3.8.2")
            self.tool_requires("flex/2.6.4")
        if self.options.with_introspection:
            self.tool_requires("gobject-introspection/1.72.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # TODO: fill in generate()
        tc = PkgConfigDeps(self)
        tc.generate()

    def _configure_meson(self):
        defs = dict()

        def add_flag(name, value):
            if name in defs:
                defs[name] += " " + value
            else:
                defs[name] = value

        def add_compiler_flag(value):
            add_flag("c_args", value)
            add_flag("cpp_args", value)

        def add_linker_flag(value):
            add_flag("c_link_args", value)
            add_flag("cpp_link_args", value)

        meson = Meson(self)
        if is_msvc(self):
            add_linker_flag("-lws2_32")
            add_compiler_flag(f"-{msvc_runtime_flag(self)}")
            if int(str(self.settings.compiler.version)) < 14:
                add_compiler_flag("-Dsnprintf=_snprintf")
        if msvc_runtime_flag(self):
            defs["b_vscrt"] = msvc_runtime_flag(self).lower()
        defs["tools"] = "disabled"
        defs["examples"] = "disabled"
        defs["benchmarks"] = "disabled"
        defs["tests"] = "disabled"
        defs["wrap_mode"] = "nofallback"
        defs["introspection"] = "enabled" if self.options.with_introspection else "disabled"
        meson.configure(build_folder=self._build_subfolder, source_folder=self.source_folder, defs=defs)
        return meson

    def build(self):
        apply_conandata_patches(self)

        with (
            environment_append(self, VisualStudioBuildEnvironment(self).vars)
            if is_msvc(self)
            else nullcontext()
        ):
            meson = self._configure_meson()
            meson.build()

    def _fix_library_names(self, path):
        # regression in 1.16
        if is_msvc(self):
            with chdir(self, path):
                for filename_old in glob.glob("*.a"):
                    filename_new = filename_old[3:-2] + ".lib"
                    self.output.info("rename %s into %s" % (filename_old, filename_new))
                    shutil.move(filename_old, filename_new)

    def package(self):
        copy(self, "COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        with (
            environment_append(self, VisualStudioBuildEnvironment(self).vars)
            if is_msvc(self)
            else nullcontext()
        ):
            meson = self._configure_meson()
            meson.install()

        self._fix_library_names(os.path.join(self.package_folder, "lib"))
        self._fix_library_names(os.path.join(self.package_folder, "lib", "gstreamer-1.0"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "gstreamer-1.0", "pkgconfig"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        plugins = [
            "accurip",
            "adpcmdec",
            "adpcmenc",
            "aiff",
            "asfmux",
            "audiobuffersplit",
            "audiofxbad",
            "audiolatency",
            "audiomixmatrix",
            "audiovisualizers",
            "autoconvert",
            "bayer",
            "camerabin",
            "codecalpha",
            "coloreffects",
            "debugutilsbad",
            "dvbsubenc",
            "dvbsuboverlay",
            "dvdspu",
            "faceoverlay",
            "festival",
            "fieldanalysis",
            "freeverb",
            "frei0r",
            "gaudieffects",
            "gdp",
            "geometrictransform",
            "id3tag",
            "inter",
            "interlace",
            "ivfparse",
            "ivtc",
            "jp2kdecimator",
            "jpegformat",
            "rfbsrc",
            "midi",
            "mpegpsdemux",
            "mpegpsmux",
            "mpegtsdemux",
            "mpegtsmux",
            "mxf",
            "netsim",
            "rtponvif",
            "pcapparse",
            "pnm",
            "proxy",
            "legacyrawparse",
            "removesilence",
            "rist",
            "rtmp2",
            "rtpmanagerbad",
            "sdpelem",
            "segmentclip",
            "siren",
            "smooth",
            "speed",
            "subenc",
            "switchbin",
            "timecode",
            "transcode",
            "videofiltersbad",
            "videoframe_audiolevel",
            "videoparsersbad",
            "videosignal",
            "vmnc",
            "y4mdec",
        ]

        gst_plugin_path = os.path.join(self.package_folder, "lib", "gstreamer-1.0")
        if self.options.shared:
            self.output.info("Appending GST_PLUGIN_PATH env var : %s" % gst_plugin_path)
            self.cpp_info.bindirs.append(gst_plugin_path)
            self.runenv_info.prepend_path("GST_PLUGIN_PATH", gst_plugin_path)
            self.env_info.GST_PLUGIN_PATH.append(gst_plugin_path)
        else:
            self.cpp_info.defines.append("GST_PLUGINS_BAD_STATIC")
            self.cpp_info.libdirs.append(gst_plugin_path)
            self.cpp_info.libs.extend(["gst%s" % plugin for plugin in plugins])

        self.cpp_info.includedirs = ["include", os.path.join("include", "gstreamer-1.0")]
