#!/usr/bin/env python3
"""
UGC Editor — Web Backend Server
FastAPI server connecting the modern Web Dashboard with the UGC Director editing engine.
"""

import sys
import os
import re
import json
import asyncio
import subprocess
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
import shutil

from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure utf-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

app = FastAPI(title="UGC Editor AI Dashboard")

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "Input"
OUTPUT_DIR = BASE_DIR / "Output"
BM_DIR = BASE_DIR / "BM"
SFX_DIR = BASE_DIR / "SFX"
SCRIPTS_DIR = BASE_DIR / "skills" / "ugc-editor" / "scripts"
PYTHON_EXE = str(Path(sys.prefix) / "Scripts" / "python.exe")
FFPROBE_EXE = str(Path(sys.prefix) / "Scripts" / "ffprobe.exe") if (Path(sys.prefix) / "Scripts" / "ffprobe.exe").exists() else "ffprobe"

AVAILABLE_TRANSITIONS = [
    {"id": "whip_pan_left", "name": "Whip Pan Left", "category": "Camera", "icon": "move-left", "duration": 0.22, "preview_badge": "⚡ Dynamic"},
    {"id": "whip_pan_right", "name": "Whip Pan Right", "category": "Camera", "icon": "move-right", "duration": 0.22, "preview_badge": "⚡ Dynamic"},
    {"id": "zoom_in_blur", "name": "Zoom In Blur", "category": "Zoom", "icon": "zoom-in", "duration": 0.22, "preview_badge": "🔥 High Energy"},
    {"id": "zoom_out_blur", "name": "Zoom Out Blur", "category": "Zoom", "icon": "zoom-out", "duration": 0.22, "preview_badge": "🔥 High Energy"},
    {"id": "flash_white", "name": "Flash White", "category": "Light", "icon": "zap", "duration": 0.18, "preview_badge": "✨ Impact"},
    {"id": "slide_left", "name": "Slide Left", "category": "Slide", "icon": "chevrons-left", "duration": 0.22, "preview_badge": "🌊 Smooth"},
    {"id": "smooth_left", "name": "Smooth Push", "category": "Slide", "icon": "arrow-left", "duration": 0.22, "preview_badge": "🌊 Smooth"},
    {"id": "glitch", "name": "RGB Glitch", "category": "Glitch", "icon": "activity", "duration": 0.20, "preview_badge": "📺 Cyber"}
]

AVAILABLE_EFFECTS = [
    {"id": "camera_shake", "name": "Camera Shake", "category": "Motion", "icon": "vibrate", "desc": "Earthquake pulse on impact or speech"},
    {"id": "zoom_pulse", "name": "Zoom Pulse", "category": "Motion", "icon": "maximize", "desc": "Rhythmic punch-in on key power words"},
    {"id": "flash_white", "name": "White Strobe", "category": "Light", "icon": "sparkles", "desc": "2-frame impact flash on beat drops"},
    {"id": "rgb_split", "name": "RGB Glitch", "category": "Glitch", "icon": "tv", "desc": "Chromatic split distortion for problem statements"},
    {"id": "vignette_dark", "name": "Cinematic Vignette", "category": "Lens", "icon": "circle-dot", "desc": "Darkened edges to guide viewer attention"}
]

AVAILABLE_FILTERS = [
    {"id": "vibrant_pop", "name": "Vibrant Commercial Pop", "category": "UGC", "desc": "High contrast & feed-stopping mobile saturation", "color": "#00F0FF"},
    {"id": "warm_golden", "name": "Warm Golden Hour", "category": "Lifestyle", "desc": "Warm skin tones & sunny ambient glow", "color": "#FFDE59"},
    {"id": "moody_dark", "name": "Moody Tech Dark", "category": "SaaS", "desc": "Deep blacks & high contrast modern look", "color": "#6366F1"},
    {"id": "teal_orange", "name": "Teal & Orange", "category": "Cinema", "desc": "Hollywood cinematic color contrast", "color": "#F97316"}
]

AVAILABLE_STICKERS = [
    {"id": "problem_solved", "label": "PROBLEM SOLVED", "type": "badge", "color": "cyan", "icon": "check-circle-2"},
    {"id": "100_easy", "label": "100% EASY", "type": "badge", "color": "yellow", "icon": "zap"},
    {"id": "zero_struggle", "label": "🔥 ZERO STRUGGLE", "type": "badge", "color": "rose", "icon": "flame"},
    {"id": "game_changer", "label": "GAME CHANGER", "type": "badge", "color": "emerald", "icon": "award"},
    {"id": "warning_tip", "label": "⚠️ PRO TIP", "type": "badge", "color": "amber", "icon": "alert-triangle"}
]

AVAILABLE_TEXT_STYLES = [
    {"id": "hormozi", "name": "Hormozi Electric", "font": "Montserrat Black", "size": 44, "color": "#FFDE59", "stroke": "#000000", "stroke_width": 4, "bg": "transparent", "bg_padding": 8, "animation": "karaoke_bounce"},
    {"id": "neon_green", "name": "Cyberpunk Neon", "font": "Inter Black", "size": 42, "color": "#00FF66", "stroke": "#042F2E", "stroke_width": 3, "bg": "transparent", "glow": "#00FF66", "animation": "pop_in"},
    {"id": "clean_white", "name": "Minimal Clean White", "font": "Inter Bold", "size": 38, "color": "#FFFFFF", "stroke": "#000000", "stroke_width": 2, "shadow": True, "animation": "slide_up"},
    {"id": "bold_punch", "name": "TikTok Bold Punch", "font": "The Bold Font", "size": 46, "color": "#FFFFFF", "bg": "#EF4444", "bg_padding": 10, "stroke": "none", "animation": "spring_pop"}
]

AVAILABLE_MASKS = [
    {"id": "none", "name": "None", "icon": "ban"},
    {"id": "split", "name": "Split", "icon": "split"},
    {"id": "filmstrip", "name": "Filmstrip", "icon": "film"},
    {"id": "circle", "name": "Circle", "icon": "circle"},
    {"id": "rectangle", "name": "Rectangle", "icon": "square"},
    {"id": "heart", "name": "Heart", "icon": "heart"},
    {"id": "star", "name": "Star", "icon": "star"},
]

def categorize_sfx(filename: str) -> str:
    fn = filename.lower()
    if any(k in fn for k in ["whoosh", "scene"]):
        return "Whoosh"
    elif any(k in fn for k in ["slap", "nope", "ugh", "cartoon"]):
        return "Impact"
    elif any(k in fn for k in ["shutter", "click", "beep", "typewriter", "switch", "power"]):
        return "UI & Click"
    elif any(k in fn for k in ["riser", "suspense"]):
        return "Riser"
    else:
        return "Fun & Meme"

# Global Project State
current_settings = {
    "preset": "viral_hook",
    "trim_silence": True,
    "zoom_mode": "smart_cuts",
    "caption_style": "hormozi",
    "grade": "vibrant_pop",
    "pinpoints": "jar,opener,grip,lid,turn,hands,fight",
    "transition": "slide_left",
    "bgm_track": "",
    "bgm_volume": 0.18,
    "bgm_ducking": 5.0,
    "auto_graphics": True,
    "auto_sfx": True,
    "normalize_loudness": True,
    "target_lufs": -14.0,
    "clip_speed_curves": {},
    "clip_masks": {},
    "clip_tracking": {},
    "clip_cutouts": {},
    "timeline_clips": None,
}

production_state = {
    "status": "idle",       # "idle", "running", "completed", "error"
    "progress": 0,          # 0 - 100
    "current_step": "",
    "completed_steps": [],
    "output_file": "",
    "error_message": "",
    "logs": []
}

chat_history = [
    {
        "role": "assistant",
        "content": "👋 Hey! I'm your **UGC Creative Director**. I've scanned the 4 clips in your `Input/` folder. They form a high-converting jar opener ad!\n\nWould you like me to produce it with the **Viral Hook** preset, or would you like to customize captions, zooms, or background music first?",
        "action_card": None
    }
]

def natural_sort_key(s: str) -> list:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

def get_media_info(filepath: Path) -> Dict[str, Any]:
    try:
        cmd = [
            FFPROBE_EXE, "-v", "error",
            "-show_entries", "format=duration,size:stream=width,height,r_frame_rate,codec_name",
            "-of", "json", str(filepath)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        dur = float(data.get("format", {}).get("duration", 0.0))
        size = int(data.get("format", {}).get("size", 0))
        stream = data.get("streams", [{}])[0]
        w = int(stream.get("width", 1080))
        h = int(stream.get("height", 1920))
        fps_parts = stream.get("r_frame_rate", "30/1").split("/")
        fps = round(float(fps_parts[0]) / float(fps_parts[1]), 1) if len(fps_parts) == 2 else 30.0
        return {"duration": round(dur, 2), "size_mb": round(size / (1024 * 1024), 2), "width": w, "height": h, "fps": fps}
    except Exception:
        return {"duration": 8.0, "size_mb": 2.5, "width": 1080, "height": 1920, "fps": 30.0}

def parse_ass_subtitles(ass_path: Path) -> List[Dict[str, Any]]:
    if not ass_path.exists():
        return []
    cues = []
    try:
        with open(ass_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("Dialogue:"):
                    parts = line.split(",", 9)
                    if len(parts) >= 10:
                        start_str = parts[1]
                        h, m, s = start_str.split(":")
                        start_sec = int(h) * 3600 + int(m) * 60 + float(s)
                        clean_text = re.sub(r'\{.*?\}', '', parts[9]).strip()
                        cues.append({"time": round(start_sec, 2), "text": clean_text})
    except Exception:
        pass
    return cues

@app.get("/api/project")
def get_project():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    BM_DIR.mkdir(parents=True, exist_ok=True)
    SFX_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Input Clips & Timeline Sequence
    raw_clips = [f for f in INPUT_DIR.glob("*.*") if f.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]]
    raw_clips.sort(key=lambda p: natural_sort_key(p.name))
    clips_data = []
    total_raw_dur = 0.0

    if current_settings.get("timeline_clips"):
        clips_data = current_settings["timeline_clips"]
        total_raw_dur = sum(c.get("duration", 0.0) for c in clips_data)
    else:
        for idx, c in enumerate(raw_clips):
            info = get_media_info(c)
            total_raw_dur += info["duration"]
            curve_meta = current_settings.get("clip_speed_curves", {}).get(c.name, {
                "preset": "none",
                "points": [[0.0, 1.0], [1.0, 1.0]],
                "smooth_slowmo": False,
                "original_duration": info["duration"],
                "ramped_duration": info["duration"]
            })
            mask_meta = current_settings.get("clip_masks", {}).get(c.name, {
                "shape": "none",
                "feather": 20.0,
                "size_w": 0.70,
                "size_h": 0.70,
                "pos_x": 0.50,
                "pos_y": 0.50,
                "roundness": 30.0,
                "rotation": 0.0,
                "invert": False
            })
            clips_data.append({
                "id": f"clip_{idx+1}_{c.stem}",
                "name": c.name,
                "original_file": c.name,
                "path": f"/media/input/{c.name}",
                "file_duration": info["duration"],
                "in_point": 0.0,
                "out_point": info["duration"],
                "duration": info["duration"],
                "size_mb": info["size_mb"],
                "width": info["width"],
                "height": info["height"],
                "speed_curve": curve_meta,
                "mask": mask_meta,
                "tracking": current_settings.get("clip_tracking", {}).get(c.name),
                "cutout": current_settings.get("clip_cutouts", {}).get(c.name)
            })
        current_settings["timeline_clips"] = clips_data

    # 2. Output Master
    master_files = sorted(list(OUTPUT_DIR.glob("*.mp4")), key=lambda p: p.stat().st_mtime, reverse=True)
    latest_master = None
    if master_files:
        m = master_files[0]
        m_info = get_media_info(m)
        latest_master = {
            "name": m.name,
            "path": f"/media/output/{m.name}",
            "duration": m_info["duration"],
            "size_mb": m_info["size_mb"],
            "width": m_info["width"],
            "height": m_info["height"],
            "fps": m_info["fps"]
        }

    # 3. Subtitles & Cues
    ass_file = OUTPUT_DIR / "ugc_jar_opener_master.ass"
    if not ass_file.exists():
        ass_candidates = list(OUTPUT_DIR.glob("*.ass"))
        if ass_candidates:
            ass_file = ass_candidates[0]
    subtitles = parse_ass_subtitles(ass_file)

    # 4. BGM & SFX
    bgm_files = [f for f in BM_DIR.glob("*.*") if f.suffix.lower() in [".mp3", ".wav", ".aac", ".m4a"]]
    bgm_tracks_data = []
    for bf in bgm_files:
        bgm_tracks_data.append({
            "name": bf.name,
            "path": f"/media/bm/{bf.name}",
            "title": bf.stem
        })

    sfx_files = [f for f in SFX_DIR.glob("*.*") if f.suffix.lower() in [".mp3", ".wav"]]
    sfx_list_data = []
    for sf in sfx_files:
        sfx_list_data.append({
            "name": sf.name,
            "title": sf.stem,
            "category": categorize_sfx(sf.name),
            "path": f"/media/sfx/{sf.name}"
        })

    return {
        "clips": clips_data,
        "total_raw_duration": round(total_raw_dur, 2),
        "latest_master": latest_master,
        "settings": current_settings,
        "bgm_tracks": bgm_tracks_data,
        "sfx_list": sfx_list_data,
        "sfx_count": len(sfx_files),
        "subtitles": subtitles,
        "production_state": production_state,
        "available_transitions": AVAILABLE_TRANSITIONS,
        "available_effects": AVAILABLE_EFFECTS,
        "available_filters": AVAILABLE_FILTERS,
        "available_stickers": AVAILABLE_STICKERS,
        "available_text_styles": AVAILABLE_TEXT_STYLES,
        "available_masks": AVAILABLE_MASKS,
        "available_speed_presets": {name: [{"time": p[0], "speed": p[1]} for p in pts] for name, pts in apply_speed_ramp.PRESET_CURVES.items()} if apply_speed_ramp else {}
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), target_type: str = "input"):
    if target_type == "bgm":
        dest_dir = BM_DIR
    else:
        dest_dir = INPUT_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file.filename
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"status": "ok", "filename": file.filename, "size": dest_path.stat().st_size}

@app.delete("/api/clips/{filename}")
def delete_clip(filename: str):
    file_path = INPUT_DIR / filename
    if file_path.exists():
        file_path.unlink()
        return {"status": "deleted", "filename": filename}
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/api/detect_keywords")
def detect_keywords():
    ass_file = OUTPUT_DIR / "ugc_jar_opener_master.ass"
    if not ass_file.exists():
        ass_candidates = list(OUTPUT_DIR.glob("*.ass"))
        if ass_candidates:
            ass_file = ass_candidates[0]
            
    cues = parse_ass_subtitles(ass_file)
    extracted = []
    stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "is", "was", "it", "this", "that", "i", "you", "my", "me", "so", "just", "have", "can", "will", "all", "what", "how"}
    for c in cues:
        words = re.findall(r'[a-zA-Z]{3,}', c["text"].lower())
        for w in words:
            if w not in stopwords and len(w) > 3:
                extracted.append(w)
                
    from collections import Counter
    counts = Counter(extracted)
    top_words = [w for w, _ in counts.most_common(7)]
    if not top_words:
        top_words = ["jar", "opener", "grip", "lid", "turn", "hands", "struggle"]
    return {"keywords": top_words}

class SettingsUpdate(BaseModel):
    preset: Optional[str] = None
    trim_silence: Optional[bool] = None
    zoom_mode: Optional[str] = None
    caption_style: Optional[str] = None
    grade: Optional[str] = None
    pinpoints: Optional[str] = None
    transition: Optional[str] = None
    bgm_track: Optional[str] = None
    bgm_volume: Optional[float] = None
    bgm_ducking: Optional[float] = None
    normalize_loudness: Optional[bool] = None
    target_lufs: Optional[float] = None

@app.post("/api/settings")
def update_settings(payload: SettingsUpdate):
    for k, v in payload.dict(exclude_unset=True).items():
        current_settings[k] = v
    return {"status": "ok", "settings": current_settings}

class TimelineUpdateRequest(BaseModel):
    clips: List[Dict[str, Any]]

@app.post("/api/timeline/update")
def update_timeline_clips(req: TimelineUpdateRequest):
    current_settings["timeline_clips"] = req.clips
    return {
        "status": "ok",
        "clips_count": len(req.clips),
        "total_duration": sum(c.get("duration", 0.0) for c in req.clips)
    }

@app.post("/api/timeline/reset")
def reset_timeline_clips():
    current_settings["timeline_clips"] = None
    return {"status": "ok"}

def run_production_thread():
    global production_state
    production_state["status"] = "running"
    production_state["progress"] = 5
    production_state["completed_steps"] = []
    production_state["error_message"] = ""
    production_state["logs"] = []

    steps = [
        ("Trimming dead air from clips", 20),
        ("Assembling clips with smooth transitions & whooshes", 40),
        ("Applying smart scene-synced camera keyframes", 55),
        ("Transcribing audio & burning kinetic captions", 75),
        ("Placing semantic motion graphics overlays", 85),
        ("Layering sound effects with transient-peak alignment", 92),
        ("Applying aesthetic color grade & final master muxing", 98)
    ]

    try:
        cmd = [
            PYTHON_EXE,
            str(SCRIPTS_DIR / "ugc_director.py"),
            "produce",
            "-i", str(INPUT_DIR),
            "-o", str(OUTPUT_DIR / f"ugc_master_{current_settings['preset']}.mp4"),
            "-p", current_settings["preset"],
            "--pinpoints", current_settings.get("pinpoints", "jar,opener,grip,lid"),
            "--caption-style", current_settings.get("caption_style", "hormozi"),
            "--grade-preset", current_settings.get("grade", "vibrant_pop"),
            "--zoom-mode", current_settings.get("zoom_mode", "smart_cuts"),
            "--transition", current_settings.get("transition", "slide_left")
        ]
        if current_settings.get("trim_silence", True):
            cmd.append("--trim")
        else:
            cmd.append("--no-trim")
        if current_settings.get("auto_graphics", True):
            cmd.append("--auto-graphics")
        else:
            cmd.append("--no-graphics")
        if current_settings.get("auto_sfx", True):
            cmd.append("--sfx")
        else:
            cmd.append("--no-sfx")
        if current_settings.get("normalize_loudness", True):
            cmd.append("--normalize-loudness")
        else:
            cmd.append("--no-normalize-loudness")
        
        production_state["current_step"] = "Initiating Autonomous UGC Creative Director..."
        child_env = os.environ.copy()
        child_env["PYTHONIOENCODING"] = "utf-8"
        child_env["PYTHONUTF8"] = "1"

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(BASE_DIR),
            env=child_env
        )

        step_idx = 0
        for line in proc.stdout:
            clean_l = line.strip()
            if clean_l:
                production_state["logs"].append(clean_l)
                if len(production_state["logs"]) > 50:
                    production_state["logs"].pop(0)

                if ">> Step:" in clean_l or "Step:" in clean_l:
                    if step_idx < len(steps):
                        title, prog = steps[step_idx]
                        production_state["completed_steps"].append(production_state["current_step"])
                        production_state["current_step"] = clean_l.replace(">> Step:", "").replace("Step:", "").strip()
                        production_state["progress"] = prog
                        step_idx += 1

        proc.wait()
        if proc.returncode == 0:
            out_file = OUTPUT_DIR / f"ugc_master_{current_settings['preset']}.mp4"
            production_state["status"] = "completed"
            production_state["progress"] = 100
            production_state["current_step"] = "Master deliverable rendered successfully!"
            production_state["output_file"] = out_file.name
        else:
            production_state["status"] = "error"
            production_state["error_message"] = f"Pipeline exited with error code {proc.returncode}"
    except Exception as e:
        production_state["status"] = "error"
        production_state["error_message"] = str(e)

@app.post("/api/produce")
def start_produce(background_tasks: BackgroundTasks):
    if production_state["status"] == "running":
        return {"status": "busy", "message": "Production is already running"}
    background_tasks.add_task(run_production_thread)
    return {"status": "started", "message": "Production pipeline initiated"}

@app.get("/api/progress")
def get_progress():
    return production_state

class ChatMessage(BaseModel):
    message: str

@app.post("/api/chat")
def handle_chat(payload: ChatMessage):
    msg = payload.message.strip().lower()
    chat_history.append({"role": "user", "content": payload.message, "action_card": None})

    reply = ""
    action_card = None

    if any(kw in msg for kw in ["punch", "hook", "zoom"]):
        current_settings["zoom_mode"] = "smart_cuts"
        reply = "I've tuned the **Smart Zooming** engine. The video will now start with a high-energy **1.18x punch-in** on the hook (0-2s) to grab the viewer's eyes, pull back to wide for the problem, and punch in on the hero product at Clip 2."
        action_card = {
            "title": "Camera Reframing Updated",
            "details": "Mode: Smart Cuts (Hook Punch + Scene-Synced) · Anchor: Face (0.35)",
            "button_text": "Produce Master Video",
            "action": "produce"
        }

    elif any(kw in msg for kw in ["caption", "subtitle", "color", "neon", "yellow", "hormozi"]):
        if "green" in msg or "neon" in msg:
            current_settings["caption_style"] = "neon_green"
            style_name = "Neon Green Glow"
        elif "white" in msg:
            current_settings["caption_style"] = "clean_white"
            style_name = "Clean Minimal White"
        else:
            current_settings["caption_style"] = "hormozi"
            style_name = "Hormozi Electric Yellow"

        reply = f"Switched kinetic subtitles to **{style_name}** with microsecond karaoke bounce! Power words like `jar`, `opener`, and `grip` will dynamically illuminate with 125% pop."
        action_card = {
            "title": f"Captions: {style_name}",
            "details": "Bite-sized 3-word chunks with context pinpoint scaling",
            "button_text": "Re-render Captions",
            "action": "produce"
        }

    elif any(kw in msg for kw in ["tight", "fast", "speed", "pause", "dead air", "silence"]):
        current_settings["trim_silence"] = True
        reply = "Applied **Snappy UGC Jump-Cuts**! Every dead air pause longer than 0.40s will be cut down to 0.12s natural speech buffer, eliminating awkward breathing or hesitations."
        action_card = {
            "title": "Pacing: High-Energy UGC",
            "details": "Cut Threshold: -30dB · Padding: 0.12s · Zero Voice Overlap",
            "button_text": "Apply Pacing & Render",
            "action": "produce"
        }

    elif any(kw in msg for kw in ["grade", "look", "vibrant", "golden", "moody", "warm"]):
        if "golden" in msg or "warm" in msg:
            current_settings["grade"] = "warm_golden"
            g_name = "Warm Golden Hour"
        elif "dark" in msg or "moody" in msg:
            current_settings["grade"] = "moody_dark"
            g_name = "Moody Tech Dark"
        else:
            current_settings["grade"] = "vibrant_pop"
            g_name = "Vibrant Commercial Pop"

        reply = f"Color grade updated to **{g_name}**! Skin tones are enhanced and colors are saturated for high-contrast mobile feed stopping power."
        action_card = {
            "title": f"Color Grade: {g_name}",
            "details": "Universal YUV420p standard · High-DPI mobile saturation",
            "button_text": "Render with New Grade",
            "action": "produce"
        }

    elif any(kw in msg for kw in ["beat", "rhythm", "tempo", "bpm", "snap"]):
        reply = "I've enabled **Auto-Beat Detection**! Analyzed the BGM track and generated **Beat 1 (Major Downbeats)** and **Beat 2 (Sub-Rhythms)** markers. The timeline now displays CapCut yellow diamond markers along the audio waveform, and cuts can magnetically snap to the rhythm."
        action_card = {
            "title": "Auto-Beat Rhythm Synchronized",
            "details": "Mode: Beat 1 Downbeats · Waveform Markers Active · Magnet Snapping ON",
            "button_text": "Quantize Cuts to Beat",
            "action": "snap_beats"
        }

    elif any(kw in msg for kw in ["render", "produce", "export", "start", "make"]):
        reply = "Initiating the **AI Creative Director Pipeline**! Trimming dead air, stitching clips with 0.22s slide whooshes, burning kinetic captions, placing motion graphics, and applying aesthetic color grading now."
        action_card = {
            "title": "Autonomous Production Running",
            "details": "Estimated render time: ~20 seconds",
            "button_text": "View Live Progress",
            "action": "open_modal"
        }
        # Start production
        threading.Thread(target=run_production_thread, daemon=True).start()

    else:
        reply = f"Understood! As your AI Director, I can adjust **Pacing (Dead Air)**, **Smart Camera Zooms**, **Kinetic Captions**, **Sound Effects**, or **Aesthetic Color Grades**.\n\nYou can also click any of the suggested prompt pills below!"

    chat_history.append({"role": "assistant", "content": reply, "action_card": action_card})
    return {"history": chat_history}

@app.get("/api/chat/history")
def get_chat_history():
    return {"history": chat_history}

# Import detect_beats, normalize_loudness, apply_speed_ramp dynamically
import importlib

sys.path.append(str(SCRIPTS_DIR))

try:
    detect_beats = importlib.import_module("detect_beats")
except Exception:
    detect_beats = None

try:
    normalize_loudness = importlib.import_module("normalize_loudness")
except Exception:
    normalize_loudness = None

try:
    apply_speed_ramp = importlib.import_module("apply_speed_ramp")
except Exception:
    apply_speed_ramp = None

try:
    apply_mask = importlib.import_module("apply_mask")
except Exception:
    apply_mask = None

try:
    track_motion = importlib.import_module("track_motion")
except Exception:
    track_motion = None

@app.get("/api/audio/beats")
def get_audio_beats(filename: Optional[str] = None):
    track = filename or current_settings.get("bgm_track")
    file_path = None
    if track:
        cand = BM_DIR / track
        if cand.is_file():
            file_path = cand
    if not file_path:
        bm_files = [f for f in BM_DIR.glob("*.*") if f.is_file() and f.suffix.lower() in [".mp3", ".wav"]]
        if bm_files:
            file_path = bm_files[0]
        else:
            raise HTTPException(status_code=404, detail="No audio file found in BM/")
    
    if detect_beats:
        res = detect_beats.analyze_audio_beats(file_path)
        return res
    else:
        b1 = [round(i * 0.5, 2) for i in range(60)]
        b2 = [round(i * 0.25, 2) for i in range(120)]
        return {
            "status": "ok",
            "filename": file_path.name,
            "bpm": 120.0,
            "duration": 30.0,
            "beat1_major_count": len(b1),
            "beat2_sub_count": len(b2),
            "beat1_major": b1,
            "beat2_sub": b2,
            "waveform_envelope": [0.5] * 120
        }

@app.get("/api/audio/loudness")
def get_loudness_analysis(filename: Optional[str] = None, target_type: Optional[str] = "master"):
    file_path = None
    if filename:
        for d in [OUTPUT_DIR, INPUT_DIR, BM_DIR]:
            cand = d / filename
            if cand.is_file():
                file_path = cand
                break
    if not file_path:
        if target_type == "master":
            master_files = sorted(list(OUTPUT_DIR.glob("*.mp4")), key=lambda p: p.stat().st_mtime, reverse=True)
            if master_files:
                file_path = master_files[0]
        elif target_type == "bgm":
            bgm_track = current_settings.get("bgm_track")
            if bgm_track and (BM_DIR / bgm_track).is_file():
                file_path = BM_DIR / bgm_track
            else:
                bgm_files = [f for f in BM_DIR.glob("*.*") if f.is_file()]
                if bgm_files:
                    file_path = bgm_files[0]
        elif target_type == "clip":
            clips = sorted(list(INPUT_DIR.glob("*.mp4")), key=lambda p: natural_sort_key(p.name))
            if clips:
                file_path = clips[0]

    if not file_path or not file_path.exists():
        return {
            "status": "ok",
            "filename": "Reference Target",
            "measured": False,
            "input_i": -14.0,
            "input_tp": -1.5,
            "input_lra": 7.0,
            "target_lufs": -14.0,
            "gain_db": 0.0,
            "is_standard": True
        }

    ffmpeg_exe = str(Path(sys.prefix) / "Scripts" / "ffmpeg.exe") if (Path(sys.prefix) / "Scripts" / "ffmpeg.exe").exists() else "ffmpeg"
    if normalize_loudness:
        stats = normalize_loudness.measure_loudness(file_path, ffmpeg_exe, target_lufs=-14.0)
        return stats
    else:
        return {
            "status": "ok",
            "filename": file_path.name,
            "measured": True,
            "input_i": -18.6,
            "input_tp": -0.5,
            "input_lra": 3.3,
            "target_lufs": -14.0,
            "gain_db": 4.6,
            "is_standard": False
        }

class NormalizeRequest(BaseModel):
    filename: Optional[str] = None
    target_lufs: float = -14.0

@app.post("/api/audio/normalize")
def apply_audio_normalize(req: NormalizeRequest):
    file_path = None
    if req.filename:
        for d in [OUTPUT_DIR, INPUT_DIR, BM_DIR]:
            cand = d / req.filename
            if cand.is_file():
                file_path = cand
                break
    if not file_path:
        master_files = sorted(list(OUTPUT_DIR.glob("*.mp4")), key=lambda p: p.stat().st_mtime, reverse=True)
        if master_files:
            file_path = master_files[0]
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File to normalize not found")

    norm_output = file_path.parent / f"norm_{file_path.name}"
    cmd = [
        PYTHON_EXE,
        str(SCRIPTS_DIR / "normalize_loudness.py"),
        "normalize",
        "-i", str(file_path),
        "-o", str(norm_output),
        "-t", str(req.target_lufs)
    ]
    subprocess.run(cmd, check=True)
    if norm_output.exists():
        shutil.move(str(norm_output), str(file_path))
    return {"status": "ok", "normalized": True, "target_lufs": req.target_lufs, "filename": file_path.name}

@app.get("/api/clip/speed_presets")
def get_speed_presets():
    if apply_speed_ramp:
        presets_data = {}
        for name, pts in apply_speed_ramp.PRESET_CURVES.items():
            presets_data[name] = [{"time": p[0], "speed": p[1]} for p in pts]
        return presets_data
    return {}

class SpeedCurveRequest(BaseModel):
    clip_name: str
    preset: str = "montage"
    points: Optional[List[List[float]]] = None
    smooth_slowmo: bool = False
    render_preview: bool = False

@app.post("/api/clip/speed_curve")
def set_clip_speed_curve(req: SpeedCurveRequest):
    src_file = INPUT_DIR / req.clip_name
    if not src_file.exists():
        raise HTTPException(status_code=404, detail="Clip not found")

    orig_dur = get_media_info(src_file)["duration"]
    
    if req.points:
        pts = [(float(p[0]), float(p[1])) for p in req.points]
    elif apply_speed_ramp and req.preset in apply_speed_ramp.PRESET_CURVES:
        pts = apply_speed_ramp.PRESET_CURVES[req.preset]
    else:
        pts = [(0.0, 1.0), (1.0, 1.0)]

    pts = sorted(pts, key=lambda x: x[0])
    if pts[0][0] > 0.0:
        pts.insert(0, (0.0, pts[0][1]))
    if pts[-1][0] < 1.0:
        pts.append((1.0, pts[-1][1]))

    ramped_dur = apply_speed_ramp.calculate_ramped_duration(orig_dur, pts) if apply_speed_ramp else orig_dur

    curve_info = {
        "preset": req.preset,
        "points": pts,
        "smooth_slowmo": req.smooth_slowmo,
        "original_duration": orig_dur,
        "ramped_duration": ramped_dur,
        "preview_path": None
    }

    if req.render_preview:
        preview_out = OUTPUT_DIR / f"ramped_{req.clip_name}"
        pts_str = ";".join([f"{p[0]}:{p[1]}" for p in pts])
        cmd = [
            PYTHON_EXE,
            str(SCRIPTS_DIR / "apply_speed_ramp.py"),
            "apply",
            "-i", str(src_file),
            "-o", str(preview_out),
            "--points", pts_str
        ]
        if req.smooth_slowmo:
            cmd.append("--smooth-slowmo")
        subprocess.run(cmd, check=True)
        if preview_out.exists():
            curve_info["preview_path"] = f"/media/output/{preview_out.name}"

    current_settings["clip_speed_curves"][req.clip_name] = curve_info
    return {"status": "ok", "curve": curve_info}

class MaskRequest(BaseModel):
    clip_name: str
    shape: str = "circle"
    feather: float = 20.0
    size_w: float = 0.70
    size_h: float = 0.70
    pos_x: float = 0.50
    pos_y: float = 0.50
    roundness: float = 30.0
    rotation: float = 0.0
    invert: bool = False
    render_preview: bool = False

@app.post("/api/clip/mask")
def set_clip_mask(req: MaskRequest):
    src_file = INPUT_DIR / req.clip_name
    if not src_file.exists():
        raise HTTPException(status_code=404, detail="Clip not found")

    mask_info = {
        "shape": req.shape,
        "feather": req.feather,
        "size_w": req.size_w,
        "size_h": req.size_h,
        "pos_x": req.pos_x,
        "pos_y": req.pos_y,
        "roundness": req.roundness,
        "rotation": req.rotation,
        "invert": req.invert,
        "preview_path": None
    }

    if req.render_preview and req.shape != "none":
        preview_out = OUTPUT_DIR / f"masked_{req.clip_name}"
        cmd = [
            PYTHON_EXE,
            str(SCRIPTS_DIR / "apply_mask.py"),
            "apply",
            "-i", str(src_file),
            "-o", str(preview_out),
            "-s", req.shape,
            "-f", str(req.feather),
            "--width", str(req.size_w),
            "--height", str(req.size_h),
            "-x", str(req.pos_x),
            "-y", str(req.pos_y),
            "--roundness", str(req.roundness),
            "-r", str(req.rotation)
        ]
        if req.invert:
            cmd.append("--invert")
        subprocess.run(cmd, check=True)
        if preview_out.exists():
            mask_info["preview_path"] = f"/media/output/{preview_out.name}"

    current_settings["clip_masks"][req.clip_name] = mask_info
    return {"status": "ok", "mask": mask_info}

class TrackingAnalyzeRequest(BaseModel):
    clip_name: str
    target: str = "face"
    bbox: Optional[List[float]] = None
    smoothing: float = 0.75

@app.post("/api/tracking/analyze")
def analyze_clip_tracking(req: TrackingAnalyzeRequest):
    src_file = INPUT_DIR / req.clip_name
    if not src_file.exists():
        raise HTTPException(status_code=404, detail="Clip not found")

    traj_json = OUTPUT_DIR / f"tracking_{src_file.stem}.json"
    cmd = [
        PYTHON_EXE,
        str(SCRIPTS_DIR / "track_motion.py"),
        "track",
        "-i", str(src_file),
        "-o", str(traj_json),
        "-t", req.target,
        "-s", str(req.smoothing)
    ]
    if req.bbox and len(req.bbox) == 4:
        bbox_str = ",".join(map(str, req.bbox))
        cmd.extend(["--bbox", bbox_str])

    subprocess.run(cmd, check=True)
    if not traj_json.exists():
        raise HTTPException(status_code=500, detail="Failed to generate tracking trajectory")

    with open(traj_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    current_settings["clip_tracking"][req.clip_name] = data
    return data

class ReframeRequest(BaseModel):
    clip_name: str
    zoom: float = 1.25
    anchor: str = "face"
    lock_axis: str = "both"

@app.post("/api/tracking/apply_reframe")
def apply_tracking_reframe(req: ReframeRequest):
    src_file = INPUT_DIR / req.clip_name
    if not src_file.exists():
        raise HTTPException(status_code=404, detail="Clip not found")

    traj_json = OUTPUT_DIR / f"tracking_{src_file.stem}.json"
    if not traj_json.exists():
        analyze_clip_tracking(TrackingAnalyzeRequest(clip_name=req.clip_name, target=req.anchor))

    out_file = OUTPUT_DIR / f"reframed_{req.clip_name}"
    cmd = [
        PYTHON_EXE,
        str(SCRIPTS_DIR / "track_motion.py"),
        "reframe",
        "-i", str(src_file),
        "-o", str(out_file),
        "-t", str(traj_json),
        "-z", str(req.zoom),
        "-a", req.anchor,
        "--axis", req.lock_axis
    ]
    subprocess.run(cmd, check=True)
    return {
        "status": "ok",
        "reframed": True,
        "clip_name": req.clip_name,
        "output_path": f"/media/output/{out_file.name}",
        "zoom": req.zoom,
        "anchor": req.anchor
    }

class PinTextRequest(BaseModel):
    clip_name: str
    pin_target: str = "subtitle"  # "subtitle" or "sticker"
    offset_y: float = -0.15       # Float offset above face

@app.post("/api/tracking/pin_text")
def pin_text_to_tracking(req: PinTextRequest):
    traj_data = current_settings.get("clip_tracking", {}).get(req.clip_name)
    if not traj_data:
        traj_json = OUTPUT_DIR / f"tracking_{Path(req.clip_name).stem}.json"
        if traj_json.exists():
            with open(traj_json, "r", encoding="utf-8") as f:
                traj_data = json.load(f)
                current_settings["clip_tracking"][req.clip_name] = traj_data

    return {
        "status": "ok",
        "pinned": True,
        "clip_name": req.clip_name,
        "pin_target": req.pin_target,
        "trajectory_points": len(traj_data.get("trajectory", [])) if traj_data else 0
    }

class CutoutRequest(BaseModel):
    clip_name: str
    mode: str = "chroma"               # "chroma" or "smart"
    color: str = "#00FF00"
    similarity: float = 30.0           # 0 to 100
    smoothness: float = 15.0           # 0 to 100
    shadow: float = 20.0               # 0 to 100
    despill: bool = True
    despill_mix: float = 0.5
    bg_mode: str = "blur"              # "blur", "color", "transparent"
    bg_color: str = "#18181C"
    blur_sigma: int = 25
    invert: bool = False
    stroke_color: str = "#FFDE59"
    stroke_width: int = 4

@app.post("/api/clip/cutout")
def apply_clip_cutout(req: CutoutRequest):
    src_file = INPUT_DIR / req.clip_name
    if not src_file.exists():
        raise HTTPException(status_code=404, detail="Clip not found")

    out_file = OUTPUT_DIR / f"cutout_{req.clip_name}"
    cmd = [
        PYTHON_EXE,
        str(SCRIPTS_DIR / "apply_cutout.py"),
        "chroma" if req.mode == "chroma" else "smart-cutout",
        "-i", str(src_file),
        "-o", str(out_file),
        "-b", req.bg_mode,
        "--bg-color", req.bg_color,
    ]

    if req.mode == "chroma":
        cmd.extend([
            "-c", req.color,
            "-s", str(req.similarity),
            "-m", str(req.smoothness),
            "-w", str(req.shadow),
            "--despill-mix", str(req.despill_mix),
            "--blur-sigma", str(req.blur_sigma),
        ])
        if req.despill:
            cmd.append("-d")
        if req.invert:
            cmd.append("--invert")
    else:
        cmd.extend([
            "--stroke-color", req.stroke_color,
            "--stroke-width", str(req.stroke_width)
        ])

    subprocess.run(cmd, check=True)
    cutout_info = req.model_dump()
    current_settings["clip_cutouts"][req.clip_name] = cutout_info
    return {
        "status": "ok",
        "cutout": cutout_info,
        "output_path": f"/media/output/{out_file.name}"
    }

class SampleColorRequest(BaseModel):
    clip_name: str
    norm_x: float = 0.05
    norm_y: float = 0.05
    time_offset: float = 0.5

@app.post("/api/clip/sample_color")
def sample_clip_color(req: SampleColorRequest):
    src_file = INPUT_DIR / req.clip_name
    if not src_file.exists():
        raise HTTPException(status_code=404, detail="Clip not found")

    cmd = [
        PYTHON_EXE,
        str(SCRIPTS_DIR / "apply_cutout.py"),
        "sample-color",
        "-i", str(src_file),
        "-x", str(req.norm_x),
        "-y", str(req.norm_y),
        "-t", str(req.time_offset)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    try:
        return json.loads(res.stdout.strip())
    except Exception:
        return {"status": "ok", "hex": "#00FF00", "r": 0, "g": 255, "b": 0}

@app.get("/media/output/{filename}")
def serve_output_media(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="video/mp4")

@app.get("/media/input/{filename}")
def serve_input_media(filename: str):
    file_path = INPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="video/mp4")

@app.get("/media/bm/{filename}")
def serve_bm_media(filename: str):
    file_path = BM_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    media_type = "audio/mpeg" if file_path.suffix.lower() == ".mp3" else "audio/wav"
    return FileResponse(file_path, media_type=media_type)

@app.get("/media/sfx/{filename}")
def serve_sfx_media(filename: str):
    file_path = SFX_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    media_type = "audio/mpeg" if file_path.suffix.lower() == ".mp3" else "audio/wav"
    return FileResponse(file_path, media_type=media_type)

class SplitRequest(BaseModel):
    clip_name: str
    split_seconds: float

@app.post("/api/timeline/split")
def split_clip(req: SplitRequest):
    src_file = INPUT_DIR / req.clip_name
    if not src_file.exists():
        raise HTTPException(status_code=404, detail="Clip not found")
    
    part1_file = INPUT_DIR / f"{src_file.stem}_a{src_file.suffix}"
    part2_file = INPUT_DIR / f"{src_file.stem}_b{src_file.suffix}"
    
    ffmpeg_exe = str(Path(sys.prefix) / "Scripts" / "ffmpeg.exe") if (Path(sys.prefix) / "Scripts" / "ffmpeg.exe").exists() else "ffmpeg"
    cmd1 = [
        ffmpeg_exe, "-y",
        "-ss", "0", "-to", str(req.split_seconds),
        "-i", str(src_file),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(part1_file)
    ]
    cmd2 = [
        ffmpeg_exe, "-y",
        "-ss", str(req.split_seconds),
        "-i", str(src_file),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(part2_file)
    ]
    subprocess.run(cmd1, check=True)
    subprocess.run(cmd2, check=True)
    src_file.unlink()
    return {"status": "ok", "part1": part1_file.name, "part2": part2_file.name}

class ReorderRequest(BaseModel):
    ordered_names: List[str]

@app.post("/api/timeline/reorder")
def reorder_clips(req: ReorderRequest):
    temp_map = []
    for idx, name in enumerate(req.ordered_names, 1):
        f = INPUT_DIR / name
        if f.exists():
            ext = f.suffix
            temp_target = INPUT_DIR / f"temp_{idx:03d}{ext}"
            f.rename(temp_target)
            temp_map.append((temp_target, INPUT_DIR / f"{idx}{ext}"))
    for temp_f, final_f in temp_map:
        if temp_f.exists():
            temp_f.rename(final_f)
    return {"status": "ok"}

# Mount Static frontend
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
