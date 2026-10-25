@echo off
rem Apre la pagina della pedana in Chrome, in una finestra dedicata
start "" chrome --app="https://ferraioligiuseppe.github.io/pnev-pedana/"
if errorlevel 1 start "" msedge --app="https://ferraioligiuseppe.github.io/pnev-pedana/"
