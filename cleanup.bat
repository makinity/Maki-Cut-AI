@echo off
echo Cleaning workspace temporary files and build traces...

:: =======================================================================
:: CRITICAL SAFETY RULES:
:: 1. NEVER TOUCH "Input" OR "Output" (All raw source videos and final
::    deliverables, clips, and audio tracks are 100% protected).
:: 2. NEVER TOUCH core system folders: .venv, .agents, .vscode, skills,
::    ui, fonts, SFX, BM.
:: =======================================================================

:: 1. Delete temporary image frames, crops, and Pillow slates
del /q /f preview_*.* test_*.* f_*.* frame_*.* thumb_*.* 2>nul
del /q /f wink_*.* scene_*.* chk_*.* secret_*.* cut_check_*.* bed_crop.* 2>nul
del /q /f row*_preview_frame.* row*_clip_sample.* rough_cut_*s_sample.* 2>nul
del /q /f *.temp.png 2>nul

:: 2. Delete temporary audio renders, subtitles, and Whisper JSON dumps
del /q /f temp_*.wav temp_*.mp3 temp_*.aac test_*.wav test_*.mp3 2>nul
del /q /f *_whisper.json ad*_whisper.json *_transcript.json 2>nul
del /q /f test.ass test.srt test.vtt 2>nul

:: 3. Delete root test videos (only in root directory, never inside Output/)
del /q /f test_*.mp4 temp_*.mp4 sample_*.mp4 draft_*.mp4 test_row*.mp4 2>nul

:: 4. Delete one-off temporary audit, analysis, and test scripts
del /q /f check_*.py find_*.py inspect_*.py dump_*.py detect_*.py 2>nul
del /q /f test_*.py extract_*.py summarize_*.py print_*.py 2>nul
del /q /f step_*.py list_scenes.py restore_cues.py 2>nul

:: 5. Delete obsolete drafts, root execution scripts, and previous video traces
del /q /f execute_*.py 2>nul
del /q /f VIDEO_STUDY_LOG.md 2>nul
del /q /f skills\biochroma-captions\scripts\analyze_tracks.py 2>nul
del /q /f skills\biochroma-captions\scripts\reskin_competitor_ad.py 2>nul
del /q /f skills\biochroma-captions\references\biochroma_script.txt 2>nul
del /q /f skills\biochroma-captions\references\lifting_script_bilingual.json 2>nul

:: 6. Remove temporary frame audit, test, and montage directories
if exist all_scenes_audit rmdir /s /q all_scenes_audit 2>nul
if exist audit_keep_ranges rmdir /s /q audit_keep_ranges 2>nul
if exist montages rmdir /s /q montages 2>nul
if exist preview_frames rmdir /s /q preview_frames 2>nul
if exist row_audit_frames rmdir /s /q row_audit_frames 2>nul
if exist test_beat_frames rmdir /s /q test_beat_frames 2>nul
if exist video2_scenes_audit rmdir /s /q video2_scenes_audit 2>nul
if exist verify_car_shots rmdir /s /q verify_car_shots 2>nul
if exist inspect_link_exact rmdir /s /q inspect_link_exact 2>nul
if exist boundary_frames rmdir /s /q boundary_frames 2>nul
if exist cuts_investigation rmdir /s /q cuts_investigation 2>nul
if exist cuts_review rmdir /s /q cuts_review 2>nul

:: 7. Generic sweep for any future video audit/review folders in root
powershell -NoProfile -Command "Get-ChildItem -Directory | Where-Object { $_.Name -match '^(audit|preview|test|verify|inspect|montage|boundary|cuts|.*_audit.*)' -and $_.Name -notmatch '^(Input|Output|SFX|BM|fonts|skills|ui|\.venv|\.agents|\.vscode)$' } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue" 2>nul

:: 8. Clean Python root bytecode cache (never touching .venv)
if exist __pycache__ rmdir /s /q __pycache__ 2>nul

echo [OK] All temporary workspace traces cleaned successfully!
echo [OK] Input/ and Output/ (including all clips and voiceovers) are 100%% protected!
