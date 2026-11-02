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

    # 1. Input Clips
    raw_clips = [f for f in INPUT_DIR.glob("*.*") if f.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]]
    raw_clips.sort(key=lambda p: natural_sort_key(p.name))
    clips_data = []
    total_raw_dur = 0.0
    for c in raw_clips:
        info = get_media_info(c)
        total_raw_dur += info["duration"]
        clips_data.append({
            "name": c.name,
            "path": f"/media/input/{c.name}",
            "duration": info["duration"],
            "size_mb": info["size_mb"],
            "width": info["width"],
            "height": info["height"]
        })

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
    bgm_tracks = [f.name for f in BM_DIR.glob("*.*") if f.suffix.lower() in [".mp3", ".wav", ".aac", ".m4a"]]
    sfx_count = len([f for f in SFX_DIR.glob("*.*") if f.suffix.lower() in [".mp3", ".wav"]])

    return {
        "clips": clips_data,
        "total_raw_duration": round(total_raw_dur, 2),
        "latest_master": latest_master,
        "settings": current_settings,
        "bgm_tracks": bgm_tracks,
        "sfx_count": sfx_count,
        "subtitles": subtitles,
        "production_state": production_state
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

@app.post("/api/settings")
def update_settings(payload: SettingsUpdate):
    for k, v in payload.dict(exclude_unset=True).items():
        current_settings[k] = v
    return {"status": "ok", "settings": current_settings}

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

# Mount Static frontend
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
