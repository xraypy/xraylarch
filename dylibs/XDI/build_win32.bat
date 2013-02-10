REM  This builds xdifile.dll for Win32 using MinGW

@echo off

REM 
REM  it assumes MinGW is installed in C:\MinGW\bin,
REM  and that MinGW msys is in C:\MinGW\msys
REM 

set oldpath=%PATH%
SET PATH=C:\MinGW\bin;C:\MinGW\MSYS\1.0\bin;C:\WINDOWS\system32;C:\WINDOWS;C:\WINDOWS\System32\Wbem;

make clean
make
gcc -shared -o xdifile.dll xdifile.o strutil.o -Wl,--add-stdcall-alias -lgcc -lm -mwindows

SET PATH=%oldpath%

