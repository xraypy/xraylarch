@echo off

REM Setup path for using compilers supplied with anaconda python 
REM This includes 64-bit Windows!


REM Location of anaconda environment
set ANAPY=C:\Users\xas_user\AppData\Local\Continuum\Anaconda\

REM Add gnuwin32 for unix tools

set Path=C:\WINDOWS\system32;C:\WINDOWS;C:\WINDOWS\System32\Wbem;
set Path=%PATH%;C:\GnuWin32\bin;%ANAPY%;%ANAPY%\Scripts;%ANAPY%\MinGW\bin

