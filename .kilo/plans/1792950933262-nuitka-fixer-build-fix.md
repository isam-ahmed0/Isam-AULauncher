# Fix Nuitka build failure for Itch_Login_Fixer on Arch Linux

## Summary

`build/build_launcher_arch_nuitka.sh` fails with:

```
mv: cannot stat 'dist/linux-nuitka/main.dist/Itch_Login_Fixer': No such file or directory
```

The second Nuitka invocation (entry point `src/fixer/Itch_Login_Fixer.py`,
`--output-filename=Itch_Login_Fixer`) produces
`dist/linux-nuitka/Itch_Login_Fixer.dist/Itch_Login_Fixer`, not
`dist/linux-nuitka/main.dist/Itch_Login_Fixer`. The `mv` on line 64 references
the wrong source path.

## Root cause

For the first build (entry point `src/launcher/main.py`,
`--output-filename=CrewLauncher`) Nuitka reports:

```
Successfully created 'dist/linux-nuitka/main.dist/CrewLauncher'
```

So `dist/linux-nuitka/main.dist/CrewLauncher` is correct there (line 36).

For the second build (entry point `src/fixer/Itch_Login_Fixer.py`,
`--output-filename=Itch_Login_Fixer`) Nuitka reports:

```
Successfully created 'dist/linux-nuitka/Itch_Login_Fixer.dist/Itch_Login_Fixer'
```

So the source for the `mv` must be
`dist/linux-nuitka/Itch_Login_Fixer.dist/Itch_Login_Fixer`, not
`main.dist/Itch_Login_Fixer`.

## Fix

Edit `build/build_launcher_arch_nuitka.sh`, line 64:

```diff
 mkdir -p dist/linux-nuitka/Itch_Login_Fixer
-mv dist/linux-nuitka/main.dist/Itch_Login_Fixer dist/linux-nuitka/Itch_Login_Fixer/
+mv dist/linux-nuitka/Itch_Login_Fixer.dist/Itch_Login_Fixer dist/linux-nuitka/Itch_Login_Fixer/
 cp -r src/fixer/assets dist/linux-nuitka/Itch_Login_Fixer/
```

## Verification

Run the build script and confirm it completes:

```bash
bash build/build_launcher_arch_nuitka.sh
```

Expected final output:

```
[nuitka-arch] Built: dist/linux-nuitka/Itch_Login_Fixer/
total ...
-rwxr-xr-x ... Itch_Login_Fixer
drwxr-xr-x ... assets
```

No `mv: cannot stat ...` error.

## Scope / notes

- Only the Arch Nuitka script is affected. The Windows scripts use PyInstaller
  (`build/build_fixer.bat`) and are unaffected.
- The first build's `mv` (line 36) is correct and should not be touched.