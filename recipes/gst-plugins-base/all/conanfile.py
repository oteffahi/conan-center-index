import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.files import chdir, copy, get, rm, rmdir
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain, Meson
from conan.tools.microsoft import is_msvc, msvc_runtime_flag
from conan.tools.scm import Version

required_conan_version = ">=1.53.0"


class GStPluginsBaseConan(ConanFile):
    name = "gst-plugins-base"
    description = "GStreamer is a development framework for creating applications like media players, video editors, streaming media broadcasters and so on"
    license = "GPL-2.0-only"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://gstreamer.freedesktop.org/"
    topics = ("gstreamer", "multimedia", "video", "audio", "broadcasting", "framework", "media")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_libalsa": [True, False],
        "with_libpng": [True, False],
        "with_libjpeg": [False, "libjpeg", "libjpeg-turbo"],
        "with_graphene": [True, False],
        "with_pango": [True, False],
        "with_ogg": [True, False],
        "with_opus": [True, False],
        "with_theora": [True, False],
        "with_vorbis": [True, False],
        "with_gl": [True, False],
        "with_egl": [True, False],
        "with_wayland": [True, False],
        "with_xorg": [True, False],
        "with_introspection": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_libalsa": True,
        "with_libpng": True,
        "with_libjpeg": "libjpeg",
        "with_graphene": True,
        "with_pango": True,
        "with_ogg": True,
        "with_opus": True,
        "with_theora": True,
        "with_vorbis": True,
        "with_gl": True,
        "with_egl": True,
        "with_wayland": True,
        "with_xorg": True,
        "with_introspection": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os not in ["Linux", "FreeBSD"]:
            self.options.rm_safe("with_libalsa")
            self.options.rm_safe("with_wayland")
        if self.settings.os not in ["Linux", "FreeBSD"]:
            self.options.rm_safe("with_egl")
            self.options.rm_safe("with_xorg")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")
        self.options["gstreamer"].shared = self.options.shared

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("gstreamer/1.22.3", transitive_headers=True)
        self.requires("glib/2.78.0", transitive_headers=True, force=True)  # FIXME: remove force
        self.requires("zlib/1.2.13")
        if self.options.get_safe("with_libalsa"):
            self.requires("libalsa/1.2.7.2")
        if self.options.get_safe("with_xorg"):
            self.requires("xorg/system", transitive_headers=True)
        if self.options.with_gl:
            self.requires("opengl/system")
            if self.settings.os == "Windows":
                self.requires("wglext/cci.20200813", transitive_headers=True)
                self.requires("glext/cci.20210420", transitive_headers=True)
            if self.options.get_safe("with_egl"):
                self.requires("egl/system", transitive_headers=True)
            if self.options.get_safe("with_wayland"):
                self.requires("wayland/1.22.0", transitive_headers=True)
                self.requires("wayland-protocols/1.31")
            if self.options.with_graphene:
                self.requires("graphene/1.10.8")
            if self.options.with_libpng:
                self.requires("libpng/1.6.40")
            if self.options.with_libjpeg == "libjpeg":
                self.requires("libjpeg/9e")
            elif self.options.with_libjpeg == "libjpeg-turbo":
                self.requires("libjpeg-turbo/3.0.0")
        if self.options.with_ogg:
            self.requires("ogg/1.3.5")
        if self.options.with_opus:
            self.requires("opus/1.4")
        if self.options.with_theora:
            self.requires("theora/1.1.1")
        if self.options.with_vorbis:
            self.requires("vorbis/1.3.7")
        if self.options.with_pango:
            self.requires("pango/1.50.14")

    def validate(self):
        if not self.dependencies["glib"].options.shared and self.options.shared:
            # https://gitlab.freedesktop.org/gstreamer/gst-build/-/issues/133
            raise ConanInvalidConfiguration("shared GStreamer cannot link to static GLib")
        if self.options.shared != self.dependencies["gstreamer"].options.shared:
            # https://gitlab.freedesktop.org/gstreamer/gst-build/-/issues/133
            raise ConanInvalidConfiguration("GStreamer and GstPlugins must be either all shared, or all static")
        if Version(self.version) >= "1.18.2" and self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < "5":
            raise ConanInvalidConfiguration(f"gst-plugins-base {self.version} does not support gcc older than 5")
        if self.options.with_gl and self.options.get_safe("with_wayland") and not self.options.get_safe("with_egl"):
            raise ConanInvalidConfiguration("OpenGL support with Wayland requires 'with_egl' turned on!")

    def build_requirements(self):
        self.tool_requires("meson/1.2.1")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/1.9.5")
        if self.settings.os == "Windows":
            self.tool_requires("winflexbison/2.5.24")
        else:
            self.tool_requires("bison/3.8.2")
            self.tool_requires("flex/2.6.4")
        if self.options.with_introspection:
            self.tool_requires("gobject-introspection/1.72.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _gl_config(self):
        gl_api = set()
        gl_platform = set()
        gl_winsys = set()  # TODO: winrt, dispamnx, viv-fb, gbm, android
        if self.options.get_safe("with_egl"):
            gl_api.add("opengl")
            gl_platform.add("egl")
            gl_winsys.add("egl")
        if self.options.get_safe("with_xorg"):
            gl_api.add("opengl")
            gl_platform.add("glx")
            gl_winsys.add("x11")
        if self.options.get_safe("with_wayland"):
            gl_api.add("opengl")
            gl_platform.add("egl")
            gl_winsys.add("wayland")
        if self.settings.os == "Macos":
            gl_api.add("opengl")
            gl_platform.add("cgl")
            gl_winsys.add("cocoa")
        elif is_apple_os(self):
            gl_api.add("gles2")
            gl_platform.add("eagl")
            gl_winsys.add("eagl")
        elif self.settings.os == "Windows":
            gl_api.add("opengl")
            gl_platform.add("wgl")
            gl_winsys.add("win32")
        return list(gl_api), list(gl_platform), list(gl_winsys)


    def generate(self):
        def add_compiler_flag(value):
            tc.c_args.append(value)
            tc.cpp_args.append(value)

        def add_linker_flag(value):
            tc.c_link_args.appened(value)
            tc.cpp_link_args.appened(value)

        tc = MesonToolchain(self)

        if is_msvc(self):
            add_linker_flag("-lws2_32")
            add_compiler_flag(f"-{msvc_runtime_flag(self)}")
            if int(str(self.settings.compiler.version)) < 14:
                add_compiler_flag("-Dsnprintf=_snprintf")
            if msvc_runtime_flag(self):
                tc.project_options["b_vscrt"] = msvc_runtime_flag(self).lower()

        gl_api, gl_platform, gl_winsys = self._gl_config()

        tc.project_options["tools"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["wrap_mode"] = "nofallback"
        tc.project_options["introspection"] = "enabled" if self.options.with_introspection else "disabled"
        tc.project_options["orc"] = "disabled"  # TODO: orc
        tc.project_options["gl"] = "enabled" if self.options.with_gl else "disabled"
        tc.project_options["gl-graphene"] = "enabled" if self.options.with_gl and self.options.with_graphene else "disabled"
        tc.project_options["gl-png"] = "enabled" if self.options.with_gl and self.options.with_libpng else "disabled"
        tc.project_options["gl-jpeg"] = "enabled" if self.options.with_gl and self.options.with_libjpeg else "disabled"
        tc.project_options["gl_api"] = gl_api
        tc.project_options["gl_platform"] = gl_platform
        tc.project_options["gl_winsys"] = gl_winsys
        tc.project_options["alsa"] = "enabled" if self.options.get_safe("with_libalsa") else "disabled"
        tc.project_options["cdparanoia"] = "disabled"  # "enabled" if self.options.with_cdparanoia else "disabled" # TODO: cdparanoia
        tc.project_options["libvisual"] = "disabled"  # "enabled" if self.options.with_libvisual else "disabled" # TODO: libvisual
        tc.project_options["ogg"] = "enabled" if self.options.with_ogg else "disabled"
        tc.project_options["opus"] = "enabled" if self.options.with_opus else "disabled"
        tc.project_options["pango"] = "enabled" if self.options.with_pango else "disabled"
        tc.project_options["theora"] = "enabled" if self.options.with_theora else "disabled"
        tc.project_options["tremor"] = "disabled"  # "enabled" if self.options.with_tremor else "disabled" # TODO: tremor - only useful on machines without floating-point support
        tc.project_options["vorbis"] = "enabled" if self.options.with_vorbis else "disabled"
        tc.project_options["x11"] = "enabled" if self.options.get_safe("with_xorg") else "disabled"
        tc.project_options["xshm"] = "enabled" if self.options.get_safe("with_xorg") else "disabled"
        tc.project_options["xvideo"] = "enabled" if self.options.get_safe("with_xorg") else "disabled"
        tc.generate()

        tc = PkgConfigDeps(self)
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def _fix_library_names(self, path):
        # regression in 1.16
        if is_msvc(self):
            with chdir(self, path):
                for filename_old in glob.glob("*.a"):
                    filename_new = filename_old[3:-2] + ".lib"
                    self.output.info(f"rename {filename_old} into {filename_new}")
                    shutil.move(filename_old, filename_new)

    def package(self):
        copy(self, pattern="COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        meson = Meson(self)
        meson.install()
        self._fix_library_names(os.path.join(self.package_folder, "lib"))
        self._fix_library_names(os.path.join(self.package_folder, "lib", "gstreamer-1.0"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "gstreamer-1.0", "pkgconfig"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        gst_plugins = []
        gst_plugin_path = os.path.join("lib", "gstreamer-1.0")
        gst_include_path = os.path.join("include", "gstreamer-1.0")

        pkgconfig_variables = {
            "exec_prefix": "${prefix}",
            "toolsdir": "${exec_prefix}/bin",
            "pluginsdir": "${libdir}/gstreamer-1.0",
            "datarootdir": "${prefix}/share",
            "datadir": "${datarootdir}",
            "girdir": "${datadir}/gir-1.0",
            "typelibdir": "${libdir}/girepository-1.0",
            "libexecdir": "${prefix}/libexec",
        }
        pkgconfig_custom_content = "\n".join(f"{key}={value}" for key, value in pkgconfig_variables.items())

        if self.options.shared:
            self.runenv_info.define_path("GST_PLUGIN_PATH", gst_plugin_path)
            # TODO: Legacy, to be removed on Conan 2.0
            self.output.info(f"Appending GST_PLUGIN_PATH env var : {gst_plugin_path}")
            self.env_info.GST_PLUGIN_PATH.append(gst_plugin_path)

        def _define_plugin_component(name, requires):
            self.cpp_info.components[name].libs = [name]
            self.cpp_info.components[name].libdirs.append(gst_plugin_path)
            self.cpp_info.components[name].requires = requires
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components[name].system_libs = ["m"]
            gst_plugins.append(name)

        # Plugins ('gst')
        _define_plugin_component("gstadder", [
            "gstreamer-audio-1.0",
            # TODO: orc
        ])
        _define_plugin_component("gstapp", [
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-app-1.0",
            "gstreamer-tag-1.0",
        ])
        _define_plugin_component("gstaudioconvert", [
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-audio-1.0",
        ])
        _define_plugin_component("gstaudiomixer", [
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-audio-1.0",
            # TODO: orc
        ])
        _define_plugin_component("gstaudiorate", [
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-audio-1.0",
        ])
        _define_plugin_component("gstaudioresample", [
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-audio-1.0",
        ])
        _define_plugin_component("gstaudiotestsrc", [
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-audio-1.0",
        ])
        _define_plugin_component("gstcompositor", [
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-video-1.0",
            # TODO: orc
        ])
        _define_plugin_component("gstencoding", [
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-video-1.0",
            "gstreamer-pbutils-1.0",
        ])
        _define_plugin_component("gstgio", [
            "gstreamer::gstreamer-base-1.0",
            "glib::gio-2.0",
        ])
        _define_plugin_component("gstoverlaycomposition", [
            "gstreamer-video-1.0",
        ])
        _define_plugin_component("gstpbtypes", [
            "gstreamer-video-1.0",
        ])
        _define_plugin_component("gstplayback", [
            "gstreamer-audio-1.0",
            "gstreamer-video-1.0",
            "gstreamer-pbutils-1.0",
            "gstreamer-tag-1.0",
        ])
        _define_plugin_component("gstrawparse", [
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-audio-1.0",
            "gstreamer-video-1.0",
        ])
        _define_plugin_component("gstsubparse", [
            "gstreamer::gstreamer-base-1.0",
        ])
        _define_plugin_component("gsttcp", [
            "gstreamer::gstreamer-base-1.0",
            "gstreamer::gstreamer-net-1.0",
            "glib::gio-2.0",
        ])
        _define_plugin_component("gsttypefindfunctions", [
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-pbutils-1.0",
            "glib::gio-2.0",
        ])
        _define_plugin_component("gstvideoconvert", [
            "gstreamer-video-1.0",
        ])
        _define_plugin_component("gstvideorate", [
            "gstreamer-video-1.0",
        ])
        _define_plugin_component("gstvideoscale", [
            "gstreamer::gstreamer-1.0",
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-video-1.0",
            "glib::glib-2.0",
            "glib::gobject-2.0",
        ])
        _define_plugin_component("gstvideotestsrc", [
            "gstreamer::gstreamer-1.0",
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-video-1.0",
            "glib::glib-2.0",
            "glib::gobject-2.0",
            # TODO: orc
        ])
        _define_plugin_component("gstvolume", [
            "gstreamer::gstreamer-1.0",
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-audio-1.0",
            "glib::glib-2.0",
            "glib::gobject-2.0",
            # TODO: orc
        ])

        # Plugins ('ext')
        if self.options.get_safe("with_libalsa"):
            _define_plugin_component("gstalsa", [
                "gstreamer::gstreamer-1.0",
                "gstreamer::gstreamer-base-1.0",
                "gstreamer-audio-1.0",
                "gstreamer-tag-1.0",
                "libalsa::libalsa",
                "glib::glib-2.0",
                "glib::gobject-2.0",
            ])

        # if self.options.with_cdparanoia:  # TODO: cdparanoia
        #     _define_plugin_component("gstcdparanoia", [
        #         "gstreamer::gstreamer-1.0",
        #         "gstreamer::gstreamer-base-1.0",
        #         "gstreamer-audio-1.0",
        #         "cdparanoia::cdparanoia",
        #         "glib::glib-2.0",
        #         "glib::gobject-2.0",
        #     ])

        if self.options.with_gl:
            _define_plugin_component("gstopengl", [
                "gstreamer::gstreamer-base-1.0",
                "gstreamer::gstreamer-controller-1.0",
                "gstreamer-video-1.0",
                "gstreamer-allocators-1.0",
                "opengl::opengl",
                # TODO: bcm
                # TODO: nvbuf_utils
            ])
            if is_apple_os(self):
                self.cpp_info.components["gstopengl"].frameworks = ["CoreFoundation", "Foundation", "QuartzCore"]
            if self.options.with_graphene:
                self.cpp_info.components["gstopengl"].requires.append("graphene::graphene-gobject-1.0")
            if self.options.with_libpng:
                self.cpp_info.components["gstopengl"].requires.append("libpng::libpng")
            if self.options.with_libjpeg == "libjpeg":
                self.cpp_info.components["gstopengl"].requires.append("libjpeg::libjpeg")
            elif self.options.with_libjpeg == "libjpeg-turbo":
                self.cpp_info.components["gstopengl"].requires.append("libjpeg-turbo::libjpeg-turbo")
            if self.options.get_safe("with_xorg"):
                self.cpp_info.components["gstopengl"].requires.append("xorg::x11")

        # if self.options.with_libvisual:  # TODO: libvisual
        #     _define_plugin_component("gstlibvisual", [
        #         "gstreamer::gstreamer-1.0",
        #         "gstreamer::gstreamer-base-1.0",
        #         "gstreamer-audio-1.0",
        #         "gstreamer-video-1.0",
        #         "gstreamer-pbutils-1.0",
        #         "libvisual::libvisual",
        #         "glib::glib-2.0",
        #         "glib::gobject-2.0",
        #     ])

        if self.options.with_ogg:
            _define_plugin_component("gstogg", [
                "gstreamer::gstreamer-1.0",
                "gstreamer::gstreamer-base-1.0",
                "gstreamer-audio-1.0",
                "gstreamer-pbutils-1.0",
                "gstreamer-tag-1.0",
                "gstreamer-riff-1.0",
                "ogg::ogglib",
                "glib::glib-2.0",
                "glib::gobject-2.0",
            ])

        if self.options.with_opus:
            _define_plugin_component("gstopus", [
                "gstreamer::gstreamer-1.0",
                "gstreamer::gstreamer-base-1.0",
                "gstreamer-audio-1.0",
                "gstreamer-pbutils-1.0",
                "gstreamer-tag-1.0",
                "opus::libopus",
                "glib::glib-2.0",
                "glib::gobject-2.0",
            ])

        if self.options.with_pango:
            _define_plugin_component("gstpango", [
                "gstreamer::gstreamer-1.0",
                "gstreamer::gstreamer-base-1.0",
                "gstreamer-video-1.0",
                "pango::pangocairo",
                "glib::glib-2.0",
                "glib::gobject-2.0",
            ])

        if self.options.with_theora:
            _define_plugin_component("gsttheora", [
                "gstreamer::gstreamer-1.0",
                "gstreamer::gstreamer-base-1.0",
                "gstreamer-video-1.0",
                "gstreamer-tag-1.0",
                "theora::theoraenc",
                "theora::theoradec",
                "glib::glib-2.0",
                "glib::gobject-2.0",
            ])

        if self.options.with_vorbis:
            _define_plugin_component("gstvorbis", [
                "gstreamer::gstreamer-1.0",
                "gstreamer::gstreamer-base-1.0",
                "gstreamer-audio-1.0",
                "gstreamer-tag-1.0",
                "vorbis::vorbismain",
                "vorbis::vorbisenc",
                "glib::glib-2.0",
                "glib::gobject-2.0",
            ])

        # if self.options.with_tremor:  # TODO: tremor
        #     _define_plugin_component("gstivorbisdec", [
        #         "gstreamer::gstreamer-1.0",
        #         "gstreamer::gstreamer-base-1.0",
        #         "gstreamer-audio-1.0",
        #         "gstreamer-tag-1.0",
        #         "tremor::tremor",
        #         "glib::glib-2.0",
        #         "glib::gobject-2.0",
        #     ])

        # Plugins ('sys')
        if self.options.get_safe("with_xorg"):
            _define_plugin_component("gstximagesink", [
                "gstreamer::gstreamer-1.0",
                "gstreamer::gstreamer-base-1.0",
                "gstreamer-video-1.0",
                "xorg::x11",
                "xorg::xext",
                "glib::glib-2.0",
                "glib::gobject-2.0",
            ])
            _define_plugin_component("gstxvimagesink", [
                "gstreamer::gstreamer-1.0",
                "gstreamer::gstreamer-base-1.0",
                "gstreamer-video-1.0",
                "xorg::x11",
                "xorg::xext",
                "xorg::xv",
                "glib::glib-2.0",
                "glib::gobject-2.0",
            ])

        # Libraries
        def _define_library_component(name, requires):
            component_name = f"gstreamer-{name}-1.0"
            self.cpp_info.components[component_name].set_property("pkg_config_name", component_name)
            self.cpp_info.components[component_name].libs = [f"gst{name}-1.0"]
            self.cpp_info.components[component_name].requires = requires
            self.cpp_info.components[component_name].includedirs = [gst_include_path]
            self.cpp_info.components[component_name].set_property("pkg_config_custom_content", pkgconfig_custom_content)
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components[component_name].system_libs = ["m"]

        _define_library_component("plugins-base", [
            "gstreamer::gstreamer-1.0",
        ])
        self.cpp_info.components["gstreamer-plugins-base-1.0"].libs = []
        if not self.options.shared:
            self.cpp_info.components["gstreamer-plugins-base-1.0"].defines.append("GST_PLUGINS_BASE_STATIC")
            self.cpp_info.components["gstreamer-plugins-base-1.0"].requires.extend(gst_plugins)
        else:
            self.cpp_info.components["gstreamer-plugins-base-1.0"].bindirs.append(gst_plugin_path)

        _define_library_component("allocators", [
            "gstreamer::gstreamer-1.0",
        ])
        _define_library_component("app", [
            "gstreamer::gstreamer-1.0",
            "gstreamer::gstreamer-base-1.0",
        ])
        _define_library_component("audio", [
            "gstreamer::gstreamer-1.0",
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-tag-1.0",
            # TODO: orc
        ])
        _define_library_component("fft", [
            "gstreamer::gstreamer-1.0",
        ])
        _define_library_component("pbutils", [
            "gstreamer::gstreamer-1.0",
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-audio-1.0",
            "gstreamer-video-1.0",
            "gstreamer-tag-1.0",
        ])
        _define_library_component("riff", [
            "gstreamer::gstreamer-1.0",
            "gstreamer-audio-1.0",
            "gstreamer-tag-1.0",
        ])
        _define_library_component("rtp", [
            "gstreamer::gstreamer-1.0",
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-audio-1.0",
        ])
        _define_library_component("rtsp", [
            "gstreamer::gstreamer-1.0",
            "gstreamer::gstreamer-base-1.0",
            "gstreamer-sdp-1.0",
            "glib::gio-2.0",
        ])
        if self.settings.os == "Windows":
            self.cpp_info.components["gstreamer-rtsp-1.0"].system_libs = ["ws2_32"]
        _define_library_component("sdp", [
            "gstreamer::gstreamer-1.0",
            "gstreamer-rtp-1.0",
            "glib::glib-2.0",
            "glib::gio-2.0",
        ])
        _define_library_component("tag", [
            "gstreamer::gstreamer-1.0",
            "gstreamer::gstreamer-base-1.0",
            "zlib::zlib",
        ])
        _define_library_component("video", [
            "gstreamer::gstreamer-1.0",
            "gstreamer::gstreamer-base-1.0",
            # TODO: orc
        ])

        if self.options.with_gl:
            _define_library_component("gl", [
                "gstreamer::gstreamer-1.0",
                "gstreamer::gstreamer-base-1.0",
                "gstreamer-allocators-1.0",
                "gstreamer-video-1.0",
                "glib::gmodule-no-export-2.0",
                "opengl::opengl",
                # TODO: bcm
            ])
            gl_api, gl_platform, gl_winsys = self._gl_config()
            gl_variables = {
                **pkgconfig_variables,
                "gl_apis": " ".join(gl_api),
                "gl_platforms": " ".join(gl_platform),
                "gl_winsys": " ".join(gl_winsys),
            }
            gl_custom_content = "\n".join(f"{key}={value}" for key, value in gl_variables.items())
            self.cpp_info.components["gstreamer-gl-1.0"].set_property("pkg_config_custom_content", gl_custom_content)

            if self.options.get_safe("with_egl"):
                self.cpp_info.components["gstreamer-gl-1.0"].requires += ["egl::egl"]
            if self.options.get_safe("with_xorg"):
                self.cpp_info.components["gstreamer-gl-1.0"].requires += ["xorg::x11", "xorg::x11-xcb"]
            if self.options.get_safe("with_wayland"):
                self.cpp_info.components["gstreamer-gl-1.0"].requires += [
                    "wayland::wayland-client",
                    "wayland::wayland-cursor",
                    "wayland::wayland-egl",
                    "wayland-protocols::wayland-protocols",
                ]
            if self.settings.os == "Windows":
                self.cpp_info.components["gstreamer-gl-1.0"].requires.append("wglext::wglext")
                self.cpp_info.components["gstreamer-gl-1.0"].requires.append("glext::glext")
                self.cpp_info.components["gstreamer-gl-1.0"].system_libs = ["gdi32"]
            if self.settings.os in ["Macos", "iOS", "tvOS", "watchOS"]:
                self.cpp_info.components["gstreamer-gl-1.0"].frameworks = [
                    "CoreFoundation",
                    "Foundation",
                    "QuartzCore",
                    "Cocoa",
                ]
            if self.settings.os in ["iOS", "tvOS", "watchOS"]:
                self.cpp_info.components["gstreamer-gl-1.0"].frameworks.extend(["CoreGraphics", "UIkit"])
            self.cpp_info.components["gstreamer-gl-1.0"].includedirs.append("include")
            self.cpp_info.components["gstreamer-gl-1.0"].includedirs.append(os.path.join(gst_plugin_path, "include"))

            self.cpp_info.components["gstreamer-gl-prototypes-1.0"].names["pkg_config"] = "gstreamer-gl-prototypes-1.0"
            self.cpp_info.components["gstreamer-gl-prototypes-1.0"].requires = [
                "gstreamer-gl-1.0",
                "opengl::opengl",
            ]

            if self.options.get_safe("with_egl"):
                self.cpp_info.components["gstreamer-gl-egl-1.0"].set_property("pkg_config_name", "gstreamer-gl-egl-1.0")
                self.cpp_info.components["gstreamer-gl-egl-1.0"].requires = [
                    "gstreamer-gl-1.0",
                    "egl::egl",
                ]

            if self.options.get_safe("with_wayland"):
                self.cpp_info.components["gstreamer-gl-wayland-1.0"].names["pkg_config"] = "gstreamer-gl-wayland-1.0"
                self.cpp_info.components["gstreamer-gl-wayland-1.0"].requires = [
                    "gstreamer-gl-1.0",
                    "wayland::wayland-client",
                    "wayland::wayland-egl",
                    "wayland-protocols::wayland-protocols",
                ]

            if self.options.get_safe("with_xorg"):
                self.cpp_info.components["gstreamer-gl-x11-1.0"].set_property("pkg_config_name", "gstreamer-gl-x11-1.0")
                self.cpp_info.components["gstreamer-gl-x11-1.0"].requires = [
                    "gstreamer-gl-1.0",
                    "xorg::x11-xcb",
                ]
