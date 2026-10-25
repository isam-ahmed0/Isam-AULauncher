# Full Fix Plan: Make CrewLauncher Faster & Faster to Build (No C++ Rewrite)

## Goal
Optimize CrewLauncher (Python + PySide6) for faster startup/runtime and faster builds without rewriting in C++. Focus on highest-ROI changes that preserve all existing functionality.

## Current State
- **Architecture**: Python 3.10+, PySide6 Qt UI, tkinter Lite fallback, toolkit-free backend (`game_core`, `network`, `file_manager`, etc.)
- **Build**: PyInstaller (onedir) on Linux/Windows, excludes many Qt modules already
- **Bottlenecks**: Large imports at module level (PySide6 in GUI), top-level heavy imports, zipfile/network operations, disk scans on startup

## Plan

### Phase 1: Measure (Baseline) 
**Goal:** Establish metrics before changes

Tasks:
1. Measure cold start time: `time python src/launcher/main.py --version` (or headless test)
2. Profile imports: `python -X importtime -c "import src.launcher.main" 2>&1 | tail -100`
3. Time builds: measure `bash build/build_launcher_linux.sh` duration
4. Profile runtime: identify slow operations (mod scanning, large zips, network)

**Validation:** Record baseline numbers in plan notes.

### Phase 2: Startup/Runtime Optimizations
**Goal:** Defer heavy imports and expensive operations

#### 2.1 Lazy imports in critical paths
- **`src/launcher/gui_qt/window/main.py`**: Many imports at top (PySide6 widgets/gui/core, mixins, managers). Move non-essential to functions where used. Keep only what's needed for class definition if possible.
- **`src/launcher/main.py`**: Already does some lazy loading - verify and extend. Ensure GUI toolkit imports stay inside functions (rule: backend must not import GUI toolkits).
- **`src/launcher/gui_qt/game.py`**: Check for top-level heavy imports
- **Other GUI files**: Audit top-level imports

#### 2.2 Defer expensive operations
- **Mod scanning**: Don't scan profiles/mods until Mods tab is opened. `mod_inspector` operations can be lazy.
- **Game size calculation**: Already done async via `_run()` in `_update_game_size()` - good. Ensure it's not blocking.
- **Version/release checks**: Already deferred with workers/splash - verify.
- **Icon loading**: Cache or load lazily.

#### 2.3 Optimize imports in backend
- **`network.py`**: `requests`, `pypresence` - pypresence only needed if Discord RPC used; already guarded.
- **`file_manager.py`**: Fine as-is
- **`game_core.py`**: Imports are reasonable

### Phase 3: Build Time Optimizations
**Goal:** Faster PyInstaller builds

#### 3.1 Build tooling
- **Use `uv`**: Switch build scripts to use `uv pip install` for faster dependency installs
- **Caching**: Ensure PyInstaller cache is used properly (`--workpath`, `--specpath` already set)
- **Parallelism**: PyInstaller uses multiprocessing; ensure system has resources

#### 3.2 PyInstaller config improvements
- **Tighten excludes**: Review all Qt modules - already aggressive. Check for others (scipy, numpy if pulled in transitively)
- **`--noupx`**: Already set (good for build speed)
- **Analyze hidden imports**: Reduce unnecessary `--hidden-import`/`--collect-submodules`
- **Spec file**: Optimize `CrewLauncher.spec` similarly

#### 3.3 Dependency trimming
- Check if all deps in `requirements.txt` are actually needed at runtime
- `packaging` is used? Check usage
- Consider if any deps can be made optional

### Phase 4: Runtime Performance Tweaks
**Goal:** Faster execution

#### 4.1 Use faster libraries where drop-in
- **JSON**: Consider `orjson` if JSON parsing is hot (config, network responses). Need to check if used heavily.
- **Zip**: `zipfile` is stdlib; could use `zipfile.ZipFile` efficiently (already doing). `shutil.unpack_archive` not used.
- **File operations**: Already using efficient patterns

#### 4.2 Threading/async
- **Downloads**: Already segmented in `network.py` - good
- **UI updates**: Using signals/workers properly

### Phase 5: Testing & Validation
**Goal:** Ensure no regressions

Tasks:
1. **Smoke test**: Run `python src/launcher/main.py --version` 
2. **Lint**: `ruff check src/launcher`
3. **Syntax**: `python -m compileall -q src/launcher`
4. **Functional test**: Test Qt UI startup, Lite fallback, basic operations
5. **Build test**: Build with PyInstaller and verify it runs
6. **Measure improvements**: Compare against baseline

## Implementation Strategy

**Order of operations:**
1. Measure baseline (Phase 1)
2. Lazy imports - highest impact on startup (Phase 2.1)
3. Defer operations (Phase 2.2)
4. Build optimizations (Phase 3)
5. Runtime tweaks (Phase 4) - only if beneficial
6. Test (Phase 5)

**Risk mitigation:**
- Make incremental changes, test after each
- Follow existing patterns (backend must not import GUI toolkits)
- Keep changes minimal and focused
- Preserve all functionality

## Specific Files to Modify

### High priority (startup)
- `src/launcher/main.py` - already good, minor tweaks
- `src/launcher/main_qt.py` - some imports could be lazy
- `src/launcher/gui_qt/window/main.py` - heavy top-level imports (PySide6, mixins, managers)
- `src/launcher/gui_qt/__init__.py` - check for imports

### Build
- `build/build_launcher_linux.sh` - add uv support
- `CrewLauncher.spec` - optimize
- `requirements-dev.txt` - add optional deps like uv hints

### Runtime (if needed)
- `src/launcher/network.py` - maybe add orjson fallback
- `src/launcher/config.py` - check if logging setup is expensive

## Success Criteria
- Faster startup time (measure with `time python src/launcher/main.py --version`)
- Faster build times
- No functionality regressions
- All existing tests/checks pass (lint, compileall)
- App runs correctly in both Qt and Tk modes

## Notes
- This is Python optimization, not C++ rewrite
- Focus on practical gains with low risk
- PySide6 import is inherently heavy but we can defer it as much as possible
- Nuitka is mentioned in discussion but plan says "without rewrite" - Nuitka is AOT compilation of Python, not a rewrite to C++ manually; it's a tool. But user said "this is python but i need c++ like fastest and fast build" and "plan the full fix without rewrite" - so better to focus on PyInstaller/Nuitka optimization within Python ecosystem.
