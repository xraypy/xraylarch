echo off
REM run all feff8l modules
SET FDIR=%~dp0

%FDIR%feff8l_rdinp
%FDIR%feff8l_pot
%FDIR%feff8l_xsph
%FDIR%feff8l_pathfinder
%FDIR%feff8l_genfmt
%FDIR%feff8l_ff2x
