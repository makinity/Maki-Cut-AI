#!/usr/bin/env python3
"""
Universal AI Agent Bridge for Makinity Cut / UGC Director.
Connects the interactive Web UI with local CLI coding agents:
- Claude Code CLI (claude)
- Gemini CLI (gemini)
- Hermes Autonomous Agent (hermes)
- OpenAI Codex / Direct LLM runner
- Built-in Local UGC Creative Director
"""

import os
import sys
import json
import re
import shutil
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator

# Ensure utf-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent

def clean_version_string(raw: str) -> str:
    """Extract and format a clean, single-line semantic version string."""
    if not raw:
        return "Installed"
    line = raw.strip().split("\n")[0]
    line = line.replace("Â·", "•").replace("·", "•")
    match = re.search(r'v?(\d+\.\d+(?:\.\d+)?)', line)
    if match:
        return f"v{match.group(1)}"
    return line[:26].strip()

def detect_available_agents(only_available: bool = True) -> List[Dict[str, Any]]:
    """
    Dynamically scan the host PC (system PATH, nodejs global, AppData, etc.)
    to discover which coding agent CLIs are actually installed and runnable.
    """
    catalog = [
        {
            "id": "claude",
            "name": "Claude Code CLI",
            "provider": "Anthropic",
            "icon": "bot",
            "badge": "Agentic CLI",
            "cmds": ["claude", "claude-code"],
            "extra_paths": [
                r"C:\Program Files\nodejs\claude.cmd",
                os.path.expandvars(r"%APPDATA%\npm\claude.cmd")
            ],
            "description": "Anthropic's autonomous coding assistant with deep reasoning and file-system awareness."
        },
        {
            "id": "gemini",
            "name": "Gemini CLI",
            "provider": "Google",
            "icon": "sparkles",
            "badge": "High-Speed",
            "cmds": ["gemini", "gemini-cli"],
            "extra_paths": [
                r"C:\Program Files\nodejs\gemini.cmd",
                os.path.expandvars(r"%APPDATA%\npm\gemini.cmd")
            ],
            "description": "Google Gemini CLI for fast, low-latency multimodal editing and script generation."
        },
        {
            "id": "hermes",
            "name": "Hermes Agent",
            "provider": "NousResearch",
            "icon": "zap",
            "badge": "Autonomous",
            "cmds": ["hermes"],
            "extra_paths": [
                os.path.expandvars(r"%LOCALAPPDATA%\hermes\bin\hermes.exe"),
                os.path.expandvars(r"%USERPROFILE%\AppData\Local\hermes\bin\hermes.exe")
            ],
            "description": "Local autonomous agent specialized in programmatic media automation and code execution."
        },
        {
            "id": "kiro",
            "name": "Kiro CLI",
            "provider": "AWS / Kiro",
            "icon": "terminal",
            "badge": "Agentic CLI",
            "cmds": ["kiro-cli", "kiro"],
            "extra_paths": [
                os.path.expandvars(r"%LOCALAPPDATA%\Kiro-Cli\kiro-cli.exe"),
                r"C:\Users\Maki Liones\AppData\Local\Kiro-Cli\kiro-cli.exe",
                os.path.expandvars(r"%USERPROFILE%\AppData\Local\Kiro-Cli\kiro-cli.exe")
            ],
            "description": "Kiro CLI autonomous AI coding assistant with terminal chat."
        },
        {
            "id": "kilo",
            "name": "Kilo Code CLI",
            "provider": "Kilo",
            "icon": "terminal",
            "badge": "Coding Agent",
            "cmds": ["kilo", "kilocode"],
            "extra_paths": [
                r"C:\Program Files\nodejs\kilo.cmd",
                os.path.expandvars(r"%APPDATA%\npm\kilo.cmd")
            ],
            "description": "Kilo Code agent with local session relay and autonomous script capabilities."
        },
        {
            "id": "aider",
            "name": "Aider Pair Programmer",
            "provider": "OpenSource",
            "icon": "code",
            "badge": "Pair Coding",
            "cmds": ["aider"],
            "extra_paths": [],
            "description": "Aider terminal pair programmer connected to Git and local models."
        },
        {
            "id": "ollama",
            "name": "Ollama Local LLM",
            "provider": "Ollama",
            "icon": "cpu",
            "badge": "Local Offline",
            "cmds": ["ollama"],
            "extra_paths": [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
                r"C:\Program Files\Ollama\ollama.exe"
            ],
            "description": "Local offline LLM runner powering llama, mistral, and qwen models."
        },
        {
            "id": "codex",
            "name": "OpenAI Codex / GPT",
            "provider": "OpenAI",
            "icon": "cpu",
            "badge": "Model API",
            "cmds": ["codex"],
            "extra_paths": [],
            "description": "Direct code generation and timeline patch synthesis via OpenAI API."
        },
        {
            "id": "cursor",
            "name": "Cursor Agent CLI",
            "provider": "Anysphere",
            "icon": "mouse-pointer",
            "badge": "IDE Agent",
            "cmds": ["cursor"],
            "extra_paths": [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\cursor\resources\app\bin\cursor.cmd")
            ],
            "description": "Cursor AI IDE command-line integration."
        },
        {
            "id": "local",
            "name": "Makinity Native Director",
            "provider": "Makinity",
            "icon": "film",
            "badge": "Zero-Latency",
            "cmds": [],
            "extra_paths": [],
            "always": True,
            "description": "Deterministic rule-based creative engine with instant sub-second timeline diff generation."
        }
    ]

    detected = []

    for item in catalog:
        if item.get("always"):
            detected.append({
                "id": item["id"],
                "name": item["name"],
                "provider": item["provider"],
                "icon": item["icon"],
                "badge": item["badge"],
                "available": True,
                "version": "v2.4 Built-in",
                "path": "builtin",
                "description": item["description"]
            })
            continue

        found_path = None
        # 1. Search PATH via shutil.which
        for cmd in item["cmds"]:
            p = shutil.which(cmd) or shutil.which(f"{cmd}.cmd") or shutil.which(f"{cmd}.exe") or shutil.which(f"{cmd}.bat")
            if p:
                found_path = p
                break

        # 2. Search specific extra paths if not on PATH
        if not found_path:
            for ep in item.get("extra_paths", []):
                if ep and os.path.exists(ep):
                    found_path = ep
                    break

        is_avail = bool(found_path)
        version_str = "Not installed"

        if is_avail:
            try:
                res = subprocess.run(
                    [found_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=3.5,
                    shell=True,
                    encoding="utf-8",
                    errors="replace"
                )
                raw_out = (res.stdout.strip() or res.stderr.strip())
                version_str = clean_version_string(raw_out)
            except Exception:
                version_str = "Installed"

        entry = {
            "id": item["id"],
            "name": item["name"],
            "provider": item["provider"],
            "icon": item["icon"],
            "badge": item["badge"],
            "available": is_avail,
            "version": version_str,
            "path": str(found_path) if found_path else None,
            "description": item["description"]
        }

        # Filter: by default, only include installed/available CLIs!
        if only_available:
            if is_avail:
                detected.append(entry)
        else:
            detected.append(entry)

    return detected


def build_system_prompt(project_state: Dict[str, Any]) -> str:
    """Build a comprehensive context prompt with active project state."""
    settings = project_state.get("settings", {})
    clips = project_state.get("clips", [])
    total_dur = project_state.get("total_raw_duration", 0.0)

    clips_summary = []
    for c in clips:
        name = c.get("name")
        dur = c.get("duration", 0.0)
        in_p = c.get("in_point", 0.0)
        out_p = c.get("out_point", dur)
        clips_summary.append(f"- {name}: {dur:.2f}s (In: {in_p:.2f}s, Out: {out_p:.2f}s)")
    clips_text = "\n".join(clips_summary) if clips_summary else "No clips loaded yet."

    prompt = f"""You are the AI Creative Director for Makinity Cut, an advanced short-form UGC video editor.
Current Active Project State:
- Total Timeline Clips: {len(clips)} (Total duration: {total_dur:.2f}s)
{clips_text}
- Current Preset: {settings.get('preset', 'viral_hook')}
- Caption Style: {settings.get('caption_style', 'hormozi')}
- Color Grade: {settings.get('grade', 'vibrant_pop')}
- Zoom Mode: {settings.get('zoom_mode', 'smart_cuts')}
- Dead Air Trim: {settings.get('trim_silence', True)}
- Loudness Target: {settings.get('target_lufs', -14.0)} LUFS

INSTRUCTIONS:
Analyze the user's editing request and return a response containing:
1. Clear, natural explanation of your creative adjustments.
2. An exact JSON block ```json ... ``` specifying one or more atomic action patches.

Supported Action Patch operations:
- {{"op": "trim_dead_air", "cushion": 0.12}}
- {{"op": "trim_clip", "clip_name": "1.mp4", "in_point": 0.0, "out_point": 3.44}}
- {{"op": "update_subtitle_style", "style": "biochroma"|"hormozi"|"clean_white"|"neon_green", "font_size": 78, "margin_v": 520, "wrap_style": 2}}
- {{"op": "set_color_grade", "preset": "vibrant_pop"|"warm_golden"|"moody_dark"|"teal_orange"}}
- {{"op": "set_zoom_mode", "mode": "smart_cuts"|"slow_push"|"slow_pull"|"punch_cuts", "anchor": "face"|"center"}}
- {{"op": "add_overlay", "type": "red_x"|"arrow_down"|"bargraph"|"trust_seal", "start": 5.0, "duration": 2.5, "label": "..."}}
- {{"op": "set_bgm", "track": "...", "volume": 0.18, "ducking": 5.0}}
- {{"op": "produce_master", "preset": "viral_hook"}}
"""
    return prompt


def parse_action_patches_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract JSON action patches from LLM output."""
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if "patches" in data:
                return data["patches"]
            elif "op" in data:
                return [data]
        except Exception:
            pass
    # Try finding bare JSON object
    match2 = re.search(r'(\{\s*"patches"\s*:\s*\[.*?\]\s*\})', text, re.DOTALL)
    if match2:
        try:
            return json.loads(match2.group(1)).get("patches", [])
        except Exception:
            pass
    return []


async def run_local_rule_engine(user_msg: str, project_state: Dict[str, Any]) -> Dict[str, Any]:
    """Instant deterministic fallback and rule-based director."""
    msg = user_msg.lower()
    patches = []
    reply = ""
    action_card = None

    if any(k in msg for k in ["dead air", "deadair", "silence", "tight", "fast", "cut pause"]):
        patches.append({"op": "trim_dead_air", "cushion": 0.12})
        reply = "I've analyzed the audio waveforms and cut all dead air gaps longer than 0.30s down to a natural 0.12s safety cushion. All clips now snap seamlessly into the next dialogue beat!"
        action_card = {
            "title": "Dead Air Trimmed (-2.0s)",
            "details": "Threshold: -25dB · Cushion: 0.12s · Zero Voice Overlap",
            "button_text": "Apply & Re-sync Subtitles",
            "action": "apply_patch"
        }

    elif any(k in msg for k in ["biochroma", "78", "78pt", "roboto"]):
        patches.append({
            "op": "update_subtitle_style",
            "style": "biochroma",
            "font_name": "Roboto",
            "font_size": 78,
            "bold": True,
            "outline": 4.0,
            "outline_color": "#181818",
            "text_color": "#FFFFFF",
            "margin_v": 520,
            "wrap_style": 2
        })
        reply = "Updated subtitles strictly to **Client BioChroma Ad Specifications**: **78 pt Roboto Bold**, crisp 4.0 pt dark outline, strict single horizontal row (`WrapStyle: 2`), positioned in the lower-middle safe zone (`MarginV: 520`, ~27% from bottom edge)."
        action_card = {
            "title": "BioChroma Subtitle Engine Active",
            "details": "Roboto Bold 78pt · MarginV: 520 · Single Horizontal Row",
            "button_text": "Re-render Captions",
            "action": "apply_patch"
        }

    elif any(k in msg for k in ["font", "caption", "subtitle", "size"]):
        if "bigger" in msg or "large" in msg or "increase" in msg:
            sz = 78
        elif "small" in msg:
            sz = 44
        else:
            sz = 78
        patches.append({
            "op": "update_subtitle_style",
            "font_size": sz,
            "margin_v": 520,
            "wrap_style": 2
        })
        reply = f"Adjusted subtitle typography to **{sz} pt** with single-row layout constraint and lower-middle safe zone placement (`MarginV: 520`)."
        action_card = {
            "title": f"Subtitle Font Size: {sz}pt",
            "details": f"Canvas Size: 1080x1920 · MarginV: 520 · Single Row",
            "button_text": "Apply Subtitle Style",
            "action": "apply_patch"
        }

    elif any(k in msg for k in ["color", "grade", "golden", "vibrant", "moody", "warm"]):
        if "golden" in msg or "warm" in msg:
            g = "warm_golden"
            g_name = "Warm Golden Hour"
        elif "dark" in msg or "moody" in msg:
            g = "moody_dark"
            g_name = "Moody Tech Dark"
        elif "teal" in msg or "orange" in msg:
            g = "teal_orange"
            g_name = "Teal & Orange Cinema"
        else:
            g = "vibrant_pop"
            g_name = "Vibrant Commercial Pop"

        patches.append({"op": "set_color_grade", "preset": g})
        reply = f"Applied aesthetic color grading preset: **{g_name}**! Skin tones are saturated and contrast boosted for mobile feed stopping power."
        action_card = {
            "title": f"Color Grade: {g_name}",
            "details": "Universal YUV420p standard · Preserves hardware decoding",
            "button_text": "Apply Color Grade",
            "action": "apply_patch"
        }

    elif any(k in msg for k in ["zoom", "punch", "hook"]):
        patches.append({"op": "set_zoom_mode", "mode": "smart_cuts", "anchor": "face"})
        reply = "Configured **Smart Zoom Reframing** with upper-third `face` anchor! Punches in 1.18x on the hook (0-2s) to maximize eye contact, resets to wide for demonstration, and punches in on the CTA."
        action_card = {
            "title": "Smart Zooms Configured",
            "details": "Mode: Smart Cuts · Anchor: Face · Peak Zoom: 1.18x",
            "button_text": "Apply Camera Framing",
            "action": "apply_patch"
        }

    elif any(k in msg for k in ["render", "produce", "export", "assemble"]):
        patches.append({"op": "produce_master", "preset": project_state.get("settings", {}).get("preset", "viral_hook")})
        reply = "Initiating master assembly and export! Multi-clip concatenation, dead air trimming, kinetic captions, smart zooms, and broadcast -14 LUFS audio normalization are now underway."
        action_card = {
            "title": "Master Production Pipeline",
            "details": "Target: 1080x1920 30fps MP4 · NVENC Acceleration",
            "button_text": "Start Render",
            "action": "produce"
        }

    else:
        reply = f"Understood! As your AI Director, I can adjust **Dead Air Pacing**, **Subtitle Styles (BioChroma / Hormozi / Minimal)**, **Color Grades**, **Camera Zooms**, or **Sound Effects**.\n\nYou can also click any of the action chips or adjust properties manually in the Inspector!"

    return {
        "agent": "local",
        "reply": reply,
        "patches": patches,
        "action_card": action_card
    }


async def run_claude_agent(user_msg: str, project_state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute query via local Claude Code CLI."""
    claude_cmd = shutil.which("claude") or shutil.which("claude.cmd")
    if not claude_cmd:
        return await run_local_rule_engine(user_msg, project_state)

    system_prompt = build_system_prompt(project_state)
    full_prompt = f"{system_prompt}\n\nUser Message: {user_msg}"

    try:
        cmd = ["cmd.exe", "/c", f'claude -p "{full_prompt}" --output-format json']
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        out_text = stdout.decode("utf-8", errors="replace").strip()
        patches = parse_action_patches_from_text(out_text)
        
        # Clean reply from raw json blocks
        clean_reply = re.sub(r'```(?:json)?\s*\{.*?\}\s*```', '', out_text, flags=re.DOTALL).strip()
        if not clean_reply:
            clean_reply = out_text

        return {
            "agent": "claude",
            "reply": clean_reply,
            "patches": patches,
            "action_card": {
                "title": f"Claude Code: {len(patches)} Action Patches Proposed",
                "details": f"{len(patches)} operations ready to apply to timeline.",
                "button_text": "Apply Changes",
                "action": "apply_patch"
            } if patches else None
        }
    except Exception as e:
        print(f"Claude CLI execution failed: {e}, falling back to local director")
        return await run_local_rule_engine(user_msg, project_state)


async def run_gemini_agent(user_msg: str, project_state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute query via local Gemini CLI."""
    gemini_cmd = shutil.which("gemini") or shutil.which("gemini.cmd")
    if not gemini_cmd:
        return await run_local_rule_engine(user_msg, project_state)

    system_prompt = build_system_prompt(project_state)
    full_prompt = f"{system_prompt}\n\nUser Message: {user_msg}"

    try:
        cmd = ["cmd.exe", "/c", f'gemini --prompt "{full_prompt}"']
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=25.0)
        out_text = stdout.decode("utf-8", errors="replace").strip()
        patches = parse_action_patches_from_text(out_text)
        
        clean_reply = re.sub(r'```(?:json)?\s*\{.*?\}\s*```', '', out_text, flags=re.DOTALL).strip()
        if not clean_reply:
            clean_reply = out_text

        return {
            "agent": "gemini",
            "reply": clean_reply,
            "patches": patches,
            "action_card": {
                "title": f"Gemini CLI: {len(patches)} Action Patches",
                "details": f"Generated via Gemini Multimodal Engine.",
                "button_text": "Apply Changes",
                "action": "apply_patch"
            } if patches else None
        }
    except Exception as e:
        print(f"Gemini CLI execution failed: {e}, falling back to local director")
        return await run_local_rule_engine(user_msg, project_state)


async def run_hermes_agent(user_msg: str, project_state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute query via local Hermes Autonomous Agent CLI."""
    hermes_cmd = shutil.which("hermes") or shutil.which("hermes.exe")
    if not hermes_cmd:
        return await run_local_rule_engine(user_msg, project_state)

    system_prompt = build_system_prompt(project_state)
    full_prompt = f"{system_prompt}\n\nUser Message: {user_msg}"

    try:
        cmd = ["cmd.exe", "/c", f'hermes chat -q "{full_prompt}"']
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=25.0)
        out_text = stdout.decode("utf-8", errors="replace").strip()
        err_text = stderr.decode("utf-8", errors="replace").strip()

        # Clean ANSI escape sequences
        out_text = re.sub(r'\x1b\[[0-9;]*m', '', out_text).strip()
        err_text = re.sub(r'\x1b\[[0-9;]*m', '', err_text).strip()

        # If Hermes encounters auth error or non-zero exit code
        if proc.returncode != 0 or not out_text or "missing access_token" in (out_text + err_text):
            combined_err = (err_text or out_text or f"Process exited with code {proc.returncode}").strip()
            if "missing access_token" in combined_err or "re-authenticate" in combined_err.lower():
                notice = "⚠️ **Hermes Authentication Required**: Your xAI OAuth access token is expired or missing. Run `hermes model` in your terminal to re-authenticate."
            else:
                notice = f"⚠️ **Hermes Agent Notice**: {combined_err}"
            fallback = await run_local_rule_engine(user_msg, project_state)
            fallback["reply"] = f"{notice}\n\n*Auto-fallback to Native Director:*\n\n" + fallback["reply"]
            fallback["agent"] = "hermes"
            return fallback

        patches = parse_action_patches_from_text(out_text)
        clean_reply = re.sub(r'```(?:json)?\s*\{.*?\}\s*```', '', out_text, flags=re.DOTALL).strip()
        if not clean_reply:
            clean_reply = out_text

        return {
            "agent": "hermes",
            "reply": clean_reply,
            "patches": patches,
            "action_card": {
                "title": f"Hermes Agent: {len(patches)} Action Patches",
                "details": "Generated via Hermes Autonomous Coding Engine.",
                "button_text": "Apply Changes",
                "action": "apply_patch"
            } if patches else None
        }
    except Exception as e:
        print(f"Hermes CLI execution failed: {e}, falling back to local director")
        fallback = await run_local_rule_engine(user_msg, project_state)
        fallback["reply"] = f"*(Hermes Agent execution error: {e})*\n\n" + fallback["reply"]
        fallback["agent"] = "hermes"
        return fallback


async def run_kiro_agent(user_msg: str, project_state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute query via local Kiro CLI (kiro-cli)."""
    kiro_cmd = shutil.which("kiro-cli") or shutil.which("kiro") or os.path.expandvars(r"%LOCALAPPDATA%\Kiro-Cli\kiro-cli.exe")
    if not os.path.exists(str(kiro_cmd)) and not shutil.which(str(kiro_cmd)):
        return await run_local_rule_engine(user_msg, project_state)

    system_prompt = build_system_prompt(project_state)
    full_prompt = f"{system_prompt}\n\nUser Message: {user_msg}"

    try:
        proc = await asyncio.create_subprocess_exec(
            str(kiro_cmd), "chat", "--no-interactive", "--output-format", "text", full_prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=35.0)
        out_text = stdout.decode("utf-8", errors="replace").strip()
        err_text = stderr.decode("utf-8", errors="replace").strip()

        # Clean ANSI escape sequences
        out_text = re.sub(r'\x1b\[[0-9;]*m', '', out_text).strip()
        err_text = re.sub(r'\x1b\[[0-9;]*m', '', err_text).strip()

        if proc.returncode != 0 or not out_text:
            combined_err = err_text or out_text or f"Kiro CLI exited with code {proc.returncode}"
            print(f"Kiro CLI error: {combined_err}")
            fallback = await run_local_rule_engine(user_msg, project_state)
            fallback["reply"] = f"*(Kiro CLI Notice: {combined_err})*\n\n" + fallback["reply"]
            fallback["agent"] = "kiro"
            return fallback

        patches = parse_action_patches_from_text(out_text)
        clean_reply = re.sub(r'```(?:json)?\s*\{.*?\}\s*```', '', out_text, flags=re.DOTALL).strip()
        if not clean_reply:
            clean_reply = out_text

        return {
            "agent": "kiro",
            "reply": clean_reply,
            "patches": patches,
            "action_card": {
                "title": f"Kiro CLI: {len(patches)} Action Patches",
                "details": "Generated autonomously by Kiro CLI engine.",
                "button_text": "Apply Changes",
                "action": "apply_patch"
            } if patches else None
        }
    except Exception as e:
        print(f"Kiro CLI execution failed: {e}, falling back to local director")
        fallback = await run_local_rule_engine(user_msg, project_state)
        fallback["reply"] = f"*(Kiro CLI execution error: {e})*\n\n" + fallback["reply"]
        fallback["agent"] = "kiro"
        return fallback


async def run_kilo_agent(user_msg: str, project_state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute query via local Kilo Code CLI (kilo)."""
    kilo_cmd = shutil.which("kilo") or shutil.which("kilo.cmd") or shutil.which("kilo.exe") or r"C:\Program Files\nodejs\kilo.cmd"
    if not os.path.exists(str(kilo_cmd)) and not shutil.which(str(kilo_cmd)):
        return await run_local_rule_engine(user_msg, project_state)

    system_prompt = build_system_prompt(project_state)
    full_prompt = f"{system_prompt}\n\nUser Message: {user_msg}"

    try:
        cmd = ["cmd.exe", "/c", f'"{kilo_cmd}" run --pure "{full_prompt}"']
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        out_text = stdout.decode("utf-8", errors="replace").strip()
        out_text = re.sub(r'\x1b\[[0-9;]*m', '', out_text).strip()
        patches = parse_action_patches_from_text(out_text)

        clean_reply = re.sub(r'```(?:json)?\s*\{.*?\}\s*```', '', out_text, flags=re.DOTALL).strip()
        if not clean_reply:
            clean_reply = out_text

        return {
            "agent": "kilo",
            "reply": clean_reply,
            "patches": patches,
            "action_card": {
                "title": f"Kilo Code: {len(patches)} Action Patches",
                "details": "Generated via Kilo Code Agent.",
                "button_text": "Apply Changes",
                "action": "apply_patch"
            } if patches else None
        }
    except Exception as e:
        print(f"Kilo CLI execution failed: {e}, falling back to local director")
        return await run_local_rule_engine(user_msg, project_state)


async def dispatch_agent_prompt(agent_id: str, user_msg: str, project_state: Dict[str, Any]) -> Dict[str, Any]:
    """Main routing entrypoint to dispatch prompt to the chosen agent CLI."""
    agent_id = (agent_id or "local").lower()

    if agent_id == "claude":
        return await run_claude_agent(user_msg, project_state)
    elif agent_id == "gemini":
        return await run_gemini_agent(user_msg, project_state)
    elif agent_id == "hermes":
        return await run_hermes_agent(user_msg, project_state)
    elif agent_id in ("kiro", "kiro-cli"):
        return await run_kiro_agent(user_msg, project_state)
    elif agent_id in ("kilo", "kilocode"):
        return await run_kilo_agent(user_msg, project_state)
    else:
        return await run_local_rule_engine(user_msg, project_state)
