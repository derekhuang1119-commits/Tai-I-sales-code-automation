@echo off
setlocal
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --windowed --name RebarConverter --paths src src/rebar_converter/gui/app.py
echo Built dist\RebarConverter\

