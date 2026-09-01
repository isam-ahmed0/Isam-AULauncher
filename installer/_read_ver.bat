@echo off
for /f "delims=" %%v in (%1) do echo !define VERSION "%%v"
