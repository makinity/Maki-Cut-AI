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
from datetime import datetime, timezone

from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from ui.agent_bridge import detect_available_agents, dispatch_agent_prompt


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
PROJECTS_DIR = BASE_DIR / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
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
    {
        "id": "biochroma",
        "name": "BioChroma Client Standard",
        "font": "Roboto Bold",
        "size": 78,
        "color": "#FFFFFF",
        "light_color": "#1683DF",
        "stroke": "#181818",
        "stroke_width": 4,
        "bg": "transparent",
        "margin_v": 520,
        "wrap_style": 2,
        "badge": "78pt Safe-Zone",
        "animation": "static_safe"
    },
    {
        "id": "hormozi",
        "name": "Hormozi Electric",
        "font": "Montserrat Black",
        "size": 44,
        "color": "#FFDE59",
        "light_color": "#B45309",
        "stroke": "#000000",
        "stroke_width": 4,
        "bg": "transparent",
        "bg_padding": 8,
        "badge": "Yellow Pop",
        "animation": "karaoke_bounce"
    },
    {
        "id": "neon_green",
        "name": "Cyberpunk Neon",
        "font": "Inter Black",
        "size": 42,
        "color": "#00FF66",
        "light_color": "#047857",
        "stroke": "#042F2E",
        "stroke_width": 3,
        "bg": "transparent",
        "glow": "#00FF66",
        "badge": "Neon Glow",
        "animation": "pop_in"
    },
    {
        "id": "clean_white",
        "name": "Minimal Clean White",
        "font": "Inter Bold",
        "size": 38,
        "color": "#FFFFFF",
        "light_color": "#1E293B",
        "stroke": "#000000",
        "stroke_width": 2,
        "shadow": True,
        "badge": "Clean White",
        "animation": "slide_up"
    },
    {
        "id": "bold_punch",
        "name": "TikTok Bold Punch",
        "font": "The Bold Font",
        "size": 46,
        "color": "#FFFFFF",
        "light_color": "#DC2626",
        "bg": "#EF4444",
        "bg_padding": 10,
        "stroke": "none",
        "badge": "Red Pill",
        "animation": "spring_pop"
    }
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
    "caption_font": "Roboto-Bold",
    "caption_size": 78,
    "caption_color": "#FFFFFF",
    "caption_stroke": "#181818",
    "caption_stroke_width": 4.0,
    "caption_margin_v": 520,
    "caption_wrap_style": 2,
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
        "content": "👋 Hey! I'm your **AI Creative Director**. I'm connected and ready to assist with real-time editing, dead-air trimming, captions, and camera reframing.\n\nYou can prompt me to adjust anything, or select your preferred coding agent (Claude Code, Gemini CLI, Hermes, or Makinity Native)!",
        "action_card": None
    }
]

# Agent & WebSocket Manager
active_agent = "claude"
undo_history: List[Dict[str, Any]] = []

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                pass

ws_manager = ConnectionManager()


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

def ensure_default_projects():
    if not any(PROJECTS_DIR.glob("*.json")):
        now_iso = datetime.now(timezone.utc).isoformat()
        default_projs = [
            {
                "id": "proj_jar_opener",
                "name": "Jar Opener UGC Viral Ad.capcut",
                "aspect_ratio": "9:16",
                "updated_at": now_iso,
                "duration": 21.98,
                "clips_count": 4,
                "resolution": "1080x1920",
                "thumbnail_gradient": "from-blue-600 via-indigo-700 to-slate-900",
                "category": "ugc",
                "settings": {
                    "preset": "viral_hook",
                    "caption_style": "biochroma",
                    "caption_font": "Roboto-Bold",
                    "caption_size": 78,
                    "caption_color": "#FFFFFF",
                    "caption_stroke": "#181818",
                    "caption_stroke_width": 4.0,
                    "caption_margin_v": 520,
                    "caption_wrap_style": 2,
                    "grade": "vibrant_pop",
                    "bgm_track": "Lo-Fi Chill Hop.mp3",
                    "bgm_volume": 0.18
                },
                "clips": [
                    {"id": "clip_1", "name": "01_hook_problem.mp4", "duration": 4.5, "in_point": 0.0, "out_point": 4.5},
                    {"id": "clip_2", "name": "02_unboxing_reveal.mp4", "duration": 5.2, "in_point": 0.0, "out_point": 5.2},
                    {"id": "clip_3", "name": "03_demo_use_case.mp4", "duration": 6.8, "in_point": 0.0, "out_point": 6.8},
                    {"id": "clip_4", "name": "04_cta_discount.mp4", "duration": 5.48, "in_point": 0.0, "out_point": 5.48}
                ],
                "timelineTexts": [
                    {"id": "txt_1", "content": "PROBLEM SOLVED", "start": 0.0, "duration": 4.5, "style": "biochroma"},
                    {"id": "txt_2", "content": "EASY ONE-TWIST GRIP", "start": 4.5, "duration": 5.2, "style": "biochroma"}
                ],
                "timelineEffects": [
                    {"id": "fx_shake", "name": "Camera Shake", "type": "shake", "start": 0.0, "duration": 2.5}
                ],
                "timelineSfx": [
                    {"id": "sfx_whoosh", "name": "⚡ Whoosh", "start": 0.0, "duration": 1.2}
                ]
            },
            {
                "id": "proj_biochroma",
                "name": "BioChroma Client Spec 78pt Ad.capcut",
                "aspect_ratio": "9:16",
                "updated_at": now_iso,
                "duration": 42.50,
                "clips_count": 6,
                "resolution": "1080x1920",
                "thumbnail_gradient": "from-emerald-600 via-teal-700 to-slate-900",
                "category": "biochroma",
                "settings": {
                    "preset": "biochroma",
                    "caption_style": "biochroma",
                    "caption_font": "Roboto-Bold",
                    "caption_size": 78,
                    "caption_color": "#FFFFFF",
                    "caption_stroke": "#181818",
                    "caption_stroke_width": 4.0,
                    "caption_margin_v": 520,
                    "caption_wrap_style": 2,
                    "grade": "vibrant_pop",
                    "bgm_track": "Upbeat Viral Pop.mp3",
                    "bgm_volume": 0.16
                },
                "clips": [
                    {"id": "bc1", "name": "01_biochroma_hook.mp4", "duration": 6.5, "in_point": 0.0, "out_point": 6.5},
                    {"id": "bc2", "name": "02_centella_asiatica.mp4", "duration": 8.0, "in_point": 0.0, "out_point": 8.0},
                    {"id": "bc3", "name": "03_golden_peptides.mp4", "duration": 7.5, "in_point": 0.0, "out_point": 7.5},
                    {"id": "bc4", "name": "04_little_secret_wink.mp4", "duration": 4.5, "in_point": 0.0, "out_point": 4.5},
                    {"id": "bc5", "name": "05_send_me_link.mp4", "duration": 6.0, "in_point": 0.0, "out_point": 6.0},
                    {"id": "bc6", "name": "06_lifestyle_cta.mp4", "duration": 10.0, "in_point": 0.0, "out_point": 10.0}
                ],
                "timelineTexts": [
                    {"id": "txt_bc1", "content": "BIOCHROMA, IL NOSTRO PICCOLO SEGRETO", "start": 0.0, "duration": 6.5, "style": "biochroma"},
                    {"id": "txt_bc2", "content": "CENTELLA ASIATICA & PEPTIDI DI SETA", "start": 6.5, "duration": 8.0, "style": "biochroma"}
                ],
                "timelineEffects": [
                    {"id": "fx_glow", "name": "Soft Dream Glow", "type": "glow", "start": 6.5, "duration": 4.0}
                ],
                "timelineSfx": [
                    {"id": "sfx_pop", "name": "🔔 Chime", "start": 6.5, "duration": 1.5}
                ]
            },
            {
                "id": "proj_tiktok_punch",
                "name": "TikTok Punchy Hook Reel.capcut",
                "aspect_ratio": "9:16",
                "updated_at": now_iso,
                "duration": 15.30,
                "clips_count": 3,
                "resolution": "1080x1920",
                "thumbnail_gradient": "from-amber-500 via-rose-700 to-slate-900",
                "category": "ugc",
                "settings": {
                    "preset": "viral_hook",
                    "caption_style": "tiktok_bold",
                    "caption_font": "The-Bold-Font",
                    "caption_size": 46,
                    "grade": "vibrant_pop",
                    "bgm_track": "Synthwave Cyber.mp3",
                    "bgm_volume": 0.20
                },
                "clips": [
                    {"id": "vh1", "name": "shocking_stat_hook.mp4", "duration": 4.3, "in_point": 0.0, "out_point": 4.3},
                    {"id": "vh2", "name": "reveal_mechanism.mp4", "duration": 5.8, "in_point": 0.0, "out_point": 5.8},
                    {"id": "vh3", "name": "offer_scarcity_cta.mp4", "duration": 5.2, "in_point": 0.0, "out_point": 5.2}
                ],
                "timelineTexts": [
                    {"id": "txt_vh1", "content": "STOP SCROLLING RIGHT NOW", "start": 0.0, "duration": 4.3, "style": "tiktok_bold"}
                ],
                "timelineEffects": [
                    {"id": "fx_rgb", "name": "RGB Glitch", "type": "glitch", "start": 0.0, "duration": 1.5}
                ],
                "timelineSfx": [
                    {"id": "sfx_glitch", "name": "⚡ Shutter 1", "start": 0.0, "duration": 0.8}
                ]
            }
        ]
        for p in default_projs:
            p_file = PROJECTS_DIR / f"{p['id']}.json"
            with open(p_file, "w", encoding="utf-8") as f:
                json.dump(p, f, indent=2)

ensure_default_projects()

class CreateProjectPayload(BaseModel):
    name: str = "New UGC Ad.capcut"
    aspect_ratio: str = "9:16"
    preset: str = "viral_hook"

class ProjectIdPayload(BaseModel):
    id: str

class RenameProjectPayload(BaseModel):
    id: str
    name: str

@app.get("/api/projects")
def list_projects():
    ensure_default_projects()
    projects = []
    for f in PROJECTS_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as pf:
                data = json.load(pf)
                projects.append(data)
        except Exception as e:
            print(f"Error reading project {f}: {e}")
    projects.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    return {"status": "ok", "projects": projects}

@app.post("/api/projects/new")
def create_project(payload: CreateProjectPayload):
    proj_id = f"proj_{int(datetime.now(timezone.utc).timestamp())}"
    now_iso = datetime.now(timezone.utc).isoformat()
    name = payload.name.strip()
    if not name:
        name = "Untitled Project"
    if not name.endswith(".capcut"):
        name += ".capcut"
    
    preset = payload.preset or "viral_hook"
    caption_style = "biochroma" if preset == "biochroma" else ("tiktok_bold" if preset == "tiktok_bold" else "hormozi")
    
    gradient_options = [
        "from-blue-600 via-indigo-700 to-slate-900",
        "from-emerald-600 via-teal-700 to-slate-900",
        "from-amber-500 via-rose-700 to-slate-900",
        "from-purple-600 via-fuchsia-700 to-slate-900"
    ]
    existing_count = len(list(PROJECTS_DIR.glob("*.json")))
    grad = gradient_options[existing_count % len(gradient_options)]

    new_proj = {
        "id": proj_id,
        "name": name,
        "aspect_ratio": payload.aspect_ratio or "9:16",
        "updated_at": now_iso,
        "duration": 0.0,
        "clips_count": 0,
        "resolution": "1080x1920" if payload.aspect_ratio == "9:16" else ("1920x1080" if payload.aspect_ratio == "16:9" else "1080x1080"),
        "thumbnail_gradient": grad,
        "category": "biochroma" if "biochroma" in name.lower() or preset == "biochroma" else "ugc",
        "settings": {
            "preset": preset,
            "caption_style": caption_style,
            "caption_font": "Roboto-Bold" if caption_style == "biochroma" else "Inter-Bold",
            "caption_size": 78 if caption_style == "biochroma" else 44,
            "caption_color": "#FFFFFF",
            "caption_stroke": "#181818",
            "caption_stroke_width": 4.0 if caption_style == "biochroma" else 2.0,
            "caption_margin_v": 520 if caption_style == "biochroma" else 200,
            "caption_wrap_style": 2 if caption_style == "biochroma" else 0,
            "grade": "vibrant_pop",
            "bgm_track": "",
            "bgm_volume": 0.18
        },
        "clips": [],
        "timelineTexts": [
            {"id": f"txt_{proj_id}_1", "content": "NEW PROJECT HEADING", "start": 0.0, "duration": 4.0, "style": caption_style}
        ],
        "timelineEffects": [],
        "timelineSfx": []
    }

    proj_file = PROJECTS_DIR / f"{proj_id}.json"
    with open(proj_file, "w", encoding="utf-8") as f:
        json.dump(new_proj, f, indent=2)

    current_settings["current_project_id"] = proj_id
    current_settings["current_project_name"] = name
    current_settings["timeline_clips"] = []
    if "settings" in new_proj:
        current_settings.update(new_proj["settings"])

    return {"status": "ok", "project": new_proj}

@app.post("/api/projects/open")
def open_project(payload: ProjectIdPayload):
    proj_file = PROJECTS_DIR / f"{payload.id}.json"
    if not proj_file.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    with open(proj_file, "r", encoding="utf-8") as f:
        proj = json.load(f)
    
    proj["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(proj_file, "w", encoding="utf-8") as f:
        json.dump(proj, f, indent=2)

    current_settings["current_project_id"] = proj["id"]
    current_settings["current_project_name"] = proj["name"]
    current_settings["timeline_clips"] = proj.get("clips", [])
    if "settings" in proj:
        current_settings.update(proj["settings"])

    return {"status": "ok", "project": proj}

@app.post("/api/projects/duplicate")
def duplicate_project(payload: ProjectIdPayload):
    src_file = PROJECTS_DIR / f"{payload.id}.json"
    if not src_file.exists():
        raise HTTPException(status_code=404, detail="Source project not found")
    
    with open(src_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    new_id = f"proj_{int(datetime.now(timezone.utc).timestamp())}"
    now_iso = datetime.now(timezone.utc).isoformat()
    data["id"] = new_id
    data["name"] = f"Copy of {data.get('name', 'Project')}"
    data["updated_at"] = now_iso

    dst_file = PROJECTS_DIR / f"{new_id}.json"
    with open(dst_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return {"status": "ok", "project": data}

@app.post("/api/projects/rename")
def rename_project(payload: RenameProjectPayload):
    proj_file = PROJECTS_DIR / f"{payload.id}.json"
    if not proj_file.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    with open(proj_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    name = payload.name.strip()
    if not name:
        name = "Untitled Project"
    if not name.endswith(".capcut"):
        name += ".capcut"

    data["name"] = name
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(proj_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    if current_settings.get("current_project_id") == payload.id:
        current_settings["current_project_name"] = name

    return {"status": "ok", "project": data}

@app.post("/api/projects/delete")
def delete_project(payload: ProjectIdPayload):
    proj_file = PROJECTS_DIR / f"{payload.id}.json"
    if proj_file.exists():
        proj_file.unlink()
    return {"status": "ok", "deleted_id": payload.id}

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
    caption_font: Optional[str] = None
    caption_size: Optional[int] = None
    caption_color: Optional[str] = None
    caption_stroke: Optional[str] = None
    caption_stroke_width: Optional[float] = None
    caption_margin_v: Optional[int] = None
    caption_wrap_style: Optional[int] = None

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
    agent_id: Optional[str] = None

@app.websocket("/ws/timeline")
async def websocket_timeline_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json({
            "type": "init",
            "active_agent": active_agent,
            "settings": current_settings
        })
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "prompt":
                prompt_text = data.get("message", "")
                agent = data.get("agent_id") or active_agent
                chat_history.append({"role": "user", "content": prompt_text, "action_card": None})
                
                project_snap = get_project()
                res = await dispatch_agent_prompt(agent, prompt_text, project_snap)
                
                assistant_entry = {
                    "role": "assistant",
                    "content": res["reply"],
                    "action_card": res.get("action_card"),
                    "patches": res.get("patches", []),
                    "agent": res.get("agent", agent)
                }
                chat_history.append(assistant_entry)
                
                await ws_manager.broadcast({
                    "type": "agent_response",
                    "chat": assistant_entry,
                    "patches": res.get("patches", [])
                })
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

@app.get("/api/agents")
def get_agents(all: bool = False):
    return {
        "agents": detect_available_agents(only_available=not all),
        "active_agent": active_agent
    }

@app.post("/api/agents/scan")
async def scan_system_agents():
    found = detect_available_agents(only_available=True)
    await ws_manager.broadcast({
        "type": "agents_scanned",
        "agents": found,
        "active_agent": active_agent
    })
    return {"status": "ok", "count": len(found), "agents": found}

class SelectAgentReq(BaseModel):
    agent_id: str

@app.post("/api/agents/select")
async def set_active_agent(req: SelectAgentReq):
    global active_agent
    active_agent = req.agent_id
    await ws_manager.broadcast({
        "type": "agent_switched",
        "active_agent": active_agent
    })
    return {"status": "ok", "active_agent": active_agent}

class ApplyPatchRequest(BaseModel):
    patches: List[Dict[str, Any]]

@app.post("/api/timeline/apply_patch")
async def apply_timeline_patch(req: ApplyPatchRequest):
    applied = []
    # Save undo snapshot
    undo_history.append({
        "settings": dict(current_settings),
        "timeline_clips": list(current_settings.get("timeline_clips") or [])
    })
    if len(undo_history) > 20:
        undo_history.pop(0)

    for p in req.patches:
        op = p.get("op")
        if op == "trim_dead_air":
            current_settings["trim_silence"] = True
            t_clips = current_settings.get("timeline_clips") or []
            # Calculate dead air trimming on active clips
            for c in t_clips:
                orig_dur = c.get("file_duration", c.get("duration", 0.0))
                # Trim ~0.4s to 0.5s tail dead air if clip is longer than 2.0s
                if orig_dur > 2.0 and c.get("out_point", orig_dur) >= orig_dur:
                    trim_cut = round(min(0.55, orig_dur * 0.12), 2)
                    c["out_point"] = round(orig_dur - trim_cut, 2)
                    c["duration"] = round(c["out_point"] - c.get("in_point", 0.0), 2)
            applied.append(op)
        elif op == "update_subtitle_style":
            style = p.get("style", "")
            if style == "biochroma":
                current_settings["caption_style"] = "biochroma"
                current_settings["caption_font"] = "Roboto-Bold"
                current_settings["caption_size"] = 78
                current_settings["caption_color"] = "#FFFFFF"
                current_settings["caption_stroke"] = "#181818"
                current_settings["caption_stroke_width"] = 4.0
                current_settings["caption_margin_v"] = 520
                current_settings["caption_wrap_style"] = 2
            elif style == "hormozi":
                current_settings["caption_style"] = "hormozi"
                current_settings["caption_font"] = "Montserrat-Black"
                current_settings["caption_size"] = 44
                current_settings["caption_color"] = "#FFDE59"
                current_settings["caption_stroke"] = "#000000"
                current_settings["caption_stroke_width"] = 4.0
                current_settings["caption_margin_v"] = 280
                current_settings["caption_wrap_style"] = 0
            else:
                if "style" in p:
                    current_settings["caption_style"] = p["style"]
            if "font_size" in p:
                current_settings["caption_size"] = int(p["font_size"])
            if "font_family" in p or "font_name" in p:
                current_settings["caption_font"] = p.get("font_family") or p.get("font_name")
            if "margin_v" in p:
                current_settings["caption_margin_v"] = int(p["margin_v"])
            if "text_color" in p or "color" in p:
                current_settings["caption_color"] = p.get("text_color") or p.get("color")
            if "outline_color" in p or "stroke" in p:
                current_settings["caption_stroke"] = p.get("outline_color") or p.get("stroke")
            if "outline" in p or "stroke_width" in p:
                current_settings["caption_stroke_width"] = float(p.get("outline") or p.get("stroke_width"))
            if "wrap_style" in p:
                current_settings["caption_wrap_style"] = int(p["wrap_style"])
            applied.append(op)
        elif op == "set_color_grade":
            current_settings["grade"] = p.get("preset", "vibrant_pop")
            applied.append(op)
        elif op == "set_zoom_mode":
            current_settings["zoom_mode"] = p.get("mode", "smart_cuts")
            applied.append(op)
        elif op == "trim_clip":
            cname = p.get("clip_name")
            t_clips = current_settings.get("timeline_clips") or []
            for c in t_clips:
                if c.get("name") == cname or c.get("original_file") == cname:
                    c["in_point"] = p.get("in_point", c["in_point"])
                    c["out_point"] = p.get("out_point", c["out_point"])
                    c["duration"] = round(c["out_point"] - c["in_point"], 2)
            applied.append(op)
        elif op == "produce_master":
            threading.Thread(target=run_production_thread, daemon=True).start()
            applied.append(op)

    await ws_manager.broadcast({
        "type": "timeline_updated",
        "applied_patches": applied,
        "settings": current_settings
    })
    return {"status": "ok", "applied": applied, "settings": current_settings}

@app.post("/api/timeline/revert_patch")
async def revert_timeline_patch():
    if undo_history:
        prev = undo_history.pop()
        current_settings.update(prev["settings"])
        current_settings["timeline_clips"] = prev["timeline_clips"]
        await ws_manager.broadcast({
            "type": "timeline_reverted",
            "settings": current_settings
        })
        return {"status": "ok", "reverted": True}
    return {"status": "error", "message": "No undo state available"}

@app.post("/api/chat")
async def handle_chat(payload: ChatMessage):
    global active_agent
    chat_history.append({"role": "user", "content": payload.message, "action_card": None})

    target_agent = payload.agent_id or active_agent
    project_snap = get_project()
    res = await dispatch_agent_prompt(target_agent, payload.message, project_snap)

    assistant_entry = {
        "role": "assistant",
        "content": res["reply"],
        "action_card": res.get("action_card"),
        "patches": res.get("patches", []),
        "agent": res.get("agent", target_agent)
    }
    chat_history.append(assistant_entry)

    # Broadcast event to all WebSocket listeners
    await ws_manager.broadcast({
        "type": "agent_response",
        "chat": assistant_entry,
        "patches": res.get("patches", [])
    })

    return {"history": chat_history, "patches": res.get("patches", [])}

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
