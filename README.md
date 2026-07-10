# CMake Arithmetic

This context defines the language for a TOML-driven CMake project generator. It separates shareable build framework choices from local machine settings.

## Language

**Project Model**:
The normalized project description produced from `project.toml`. It is the canonical source for names, C++ standard, Qt mode, preset shape, and dependency intent.
_Avoid_: Raw TOML, script options

**CMake Framework**:
The generated project skeleton made from the template directory and the project model. It includes root CMake configuration, target CMake configuration, helper modules, dependencies, and presets.
_Avoid_: Template copy, cmake files

**Public Presets**:
Shareable preset bases stored in `CMakePresets.json`. They describe common generator, compiler, Qt, and non-Qt foundations without embedding local SDK paths.
_Avoid_: Common presets, checked-in user presets

**User Presets**:
Local preset entries stored in `CMakeUserPresets.json`. They bind public preset bases to machine-specific values such as Qt SDK and vcpkg paths.
_Avoid_: Private presets, local config

**Build Tree**:
The preset-specific developer build directory under `out/build/<presetName>`. It contains CMake cache files, Ninja files, objects, generated files, and transient build artifacts.
_Avoid_: Output folder, bin dir

**Build Artifacts**:
Compiler and linker outputs kept inside the build tree under `artifacts/<BuildType>/<arch>`. They are useful during development but are not the deployment layout.
_Avoid_: Install files, deploy files

**Install Tree**:
The clean deployment/import layout under `out/install/<presetGroup>`. It is organized like a vcpkg installed triplet, with Release outputs in `bin`/`lib`, Debug outputs in `debug/bin`/`debug/lib`, and RelWithDebInfo outputs in `relwithdebinfo/bin`/`relwithdebinfo/lib`.
_Avoid_: Build directory, temporary output

**Preset Group**:
The compiler, architecture, and optional Qt prefix shared by multiple build types, such as `msvc_x64` or `qt_msvc_x64`. It is used to group Debug, Release, and RelWithDebInfo installs under one install tree.
_Avoid_: Preset name, build type

**Qt Mode**:
A generation mode where Qt support is enabled and presets supply a Qt SDK through the `QTDIR` environment variable.
_Avoid_: GUI mode

**Non-Qt Mode**:
A generation mode where Qt support is disabled and presets are generated for the configured native C++ compilers.
_Avoid_: Console mode
