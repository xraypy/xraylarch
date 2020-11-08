
REM # use pip to install some known-safe-for-pip packages
%PREFIX%\Scripts\pip.exe install lmfit peakutils pyepics pyshortcuts termcolor xraydb wxmplot wxutils xraylarch

sleep 1

REM # make desktop icons
%PREFIX%\Scripts\larch.exe -m


echo '# Larch post install done!'
sleep 10
