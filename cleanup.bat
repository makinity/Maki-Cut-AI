@echo off
echo Cleaning workspace traces...
del /q /f temp_*.wav 2>nul
del /q /f preview_*.jpg 2>nul
del /q /f preview_*.png 2>nul
del /q /f *_whisper.json 2>nul
del /q /f ad*_whisper.json 2>nul
del /q /f test.ass 2>nul
del /q /f Output\test_*.mp4 2>nul
if exist preview_frames del /q /f preview_frames\*.* 2>nul
del /q /f generate_ad*.py 2>nul
del /q /f generate_h*.py 2>nul
del /q /f align_*.py 2>nul
del /q /f transcribe_*.py 2>nul
echo [OK] All traces cleaned successfully!
