#!/usr/bin/env python3
"""
UGC Creative Director & Master Pipeline Orchestrator.
Autonomous AI Video Editor that brings genuine human-like creativity, retention psychology,
and semantic visual storytelling to UGC and short-form video creation.

Features:
- Semantic Content Analysis: Automatically listens to what the creator says and schedules
  context-matching morphing shapes (bar graphs on growth claims, circular meters on stats,
  callout cards on pro-tips).
- The 'Hook -> Value -> CTA' Retention Architecture: High-energy pattern interrupts in the first 3s,
  multi-camera punch cuts during value delivery, and focused outro framing.
- Intelligent Audio Harmonization: Micro-SFX synced to subtitle pinpoints, whooshes on shape
  entrances, and background music sidechain-ducked so speech stays crisp.
"""

import sys
import os
import subprocess
import json
import re
import math
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Autonomous UGC Creative Director & Master Pipeline.")
console = Console(highlight=False)

PYTHON_EXE = str(Path(sys.prefix) / "Scripts" / "python.exe")
SCRIPT_DIR = Path(__file__).resolve().parent

STYLE_PRESETS = {
    "viral_hook": {
        "description": "High-retention TikTok/Reels style: fast pacing, smart cuts, vibrant grade, whooshes, and Hormozi captions.",
        "grade": "vibrant_pop",
        "zoom_mode": "smart_cuts",
        "caption_style": "hormozi",
        "transition": "slide_left",
        "shape_color": "cyan"
    },
    "storyteller": {
        "description": "Cinematic narrative look: warm golden hour grade, continuous slow push zoom, subtle risers.",
        "grade": "warm_golden",
        "zoom_mode": "slow_push",
        "caption_style": "clean_white",
        "transition": "smooth_left",
        "shape_color": "yellow"
    },
    "saas_explainer": {
        "description": "Tech product & growth look: dark modern grade, bar graph overlays, neon green accents, and UI beeps.",
        "grade": "moody_dark",
        "zoom_mode": "smart_cuts",
        "caption_style": "neon_green",
        "transition": "zoom_in",
        "shape_color": "green"
    }
}

SEMANTIC_GRAPHIC_TRIGGERS = {
    "bargraph": {
        "keywords": ["grow", "growth", "sale", "sales", "revenue", "dollar", "$", "increased", "double", "triple", "chart", "metrics"],
        "default_label": "+350% GROWTH"
    },
    "circular_motion": {
        "keywords": ["percent", "%", "rate", "10x", "speed", "score", "efficiency", "stats", "proven", "ratio", "turn", "adjust", "easy"],
        "default_label": "100% EASY"
    },
    "rectangle": {
        "keywords": ["tip", "rule", "step", "secret", "mistake", "warning", "remember", "hack", "watch", "important", "alert", "opener", "solution", "found", "jar"],
        "default_label": "PROBLEM SOLVED"
    },
    "badge_callout": {
        "keywords": ["viral", "crazy", "insane", "stop", "never", "best", "worst", "game changer", "cheat code", "formula", "mind blowing", "fight", "better grip", "struggle"],
        "default_label": "🔥 ZERO STRUGGLE"
    }
}

def run_step(cmd_args: List[str], step_title: str) -> None:
    console.print(f"\n[bold cyan]>> Step: {step_title}[/bold cyan]")
    cmd = [PYTHON_EXE] + cmd_args
    subprocess.run(cmd, check=True)

def scan_transcript_for_creative_cues(ass_file: Path) -> List[Dict[str, Any]]:
    if not ass_file.exists():
        return []
        
    dialogue_events = []
    with open(ass_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) >= 10:
                    start_str = parts[1]
                    h, m, s = start_str.split(":")
                    start_sec = int(h) * 3600 + int(m) * 60 + float(s)
                    clean_text = re.sub(r'\{.*?\}', '', parts[9]).strip()
                    dialogue_events.append({"time": start_sec, "text": clean_text})
                    
    scheduled_shapes = []
    last_shape_time = -10.0
    
    for ev in dialogue_events:
        t = ev["time"]
        txt = ev["text"].lower()
        if t - last_shape_time < 5.0:
            continue
            
        matched_shape = None
        matched_label = None
        
        for shape_type, trigger_info in SEMANTIC_GRAPHIC_TRIGGERS.items():
            for kw in trigger_info["keywords"]:
                if kw in txt:
                    matched_shape = shape_type
                    matched_label = trigger_info["default_label"]
                    for token in ev["text"].split():
                        clean_tok = re.sub(r'[^a-zA-Z0-9$%]', '', token)
                        if clean_tok.startswith("$") or clean_tok.endswith("%") or clean_tok.isdigit():
                            matched_label = clean_tok
                            break
                    break
            if matched_shape:
                break
                
        if matched_shape:
            scheduled_shapes.append({
                "shape": matched_shape,
                "start": max(0.5, t - 0.2),
                "duration": 2.8,
                "label": matched_label
            })
            last_shape_time = t
            
    return scheduled_shapes

@app.command(name="presets")
def list_presets():
    """List available automated creative editing presets."""
    for name, p in STYLE_PRESETS.items():
        console.print(Panel(
            f"[yellow]{p['description']}[/yellow]\n"
            f"Grade: [cyan]{p['grade']}[/cyan] | Zoom: [cyan]{p['zoom_mode']}[/cyan] | Captions: [cyan]{p['caption_style']}[/cyan] | Shapes: [cyan]{p['shape_color']}[/cyan]",
            title=f"[bold green]{name.upper()}[/bold green]"
        ))

@app.command(name="produce")
def produce_video(
    input_source: Path = typer.Option(Path("Input"), "--input", "-i", help="Directory or video file in Input/"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Final output path in Output/"),
    preset: str = typer.Option("viral_hook", "--preset", "-p", help="Creative preset: viral_hook, storyteller, saas_explainer"),
    trim_silence: bool = typer.Option(True, "--trim/--no-trim", help="Automatically cut dead air"),
    add_captions: bool = typer.Option(True, "--captions/--no-captions", help="Burn kinetic captions"),
    add_zooms: bool = typer.Option(True, "--zooms/--no-zooms", help="Apply dynamic camera reframing"),
    auto_graphics: bool = typer.Option(True, "--auto-graphics/--no-graphics", help="Semantically place context morphing shapes (bar graphs, rings, callouts)"),
    add_sfx_layers: bool = typer.Option(True, "--sfx/--no-sfx", help="Layer sound effects"),
    add_bgm_track: bool = typer.Option(True, "--bgm/--no-bgm", help="Mix background music with voice ducking"),
    apply_grade: bool = typer.Option(True, "--grade/--no-grade", help="Apply aesthetic color grading"),
    custom_pinpoints: Optional[str] = typer.Option(None, "--pinpoints", help="Context emphasis keywords (e.g. 'growth,sales,secret')")
):
    """
    Directs and produces a complete, polished, viral UGC video from raw inputs
    using semantic content awareness and retention psychology.
    """
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = output_dir / "temp_scratch"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    cfg = STYLE_PRESETS.get(preset.lower(), STYLE_PRESETS["viral_hook"])
    
    console.print(Panel(
        f"[bold]Selected Creative Preset:[/bold] [yellow]{preset.upper()}[/yellow]\n"
        f"[bold]Creative Strategy:[/bold] {cfg['description']}",
        title="[bold green]UGC CREATIVE DIRECTOR - AUTONOMOUS VIRAL PIPELINE[/bold green]"
    ))

    current_video = None
    if input_source.is_dir():
        raw_clips = [f for f in input_source.iterdir() if f.is_file() and f.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]]
        if not raw_clips:
            console.print(f"[bold red]Error: No video clips found in '{input_source}'![/bold red]")
            raise typer.Exit(1)
        elif len(raw_clips) == 1:
            current_video = raw_clips[0]
            if trim_silence:
                trimmed_video = temp_dir / "step2_trimmed.mp4"
                run_step([
                    str(SCRIPT_DIR / "cut_dead_air.py"),
                    "-i", str(current_video),
                    "-o", str(trimmed_video),
                    "-n", "-30.0",
                    "-s", "0.40",
                    "-p", "0.12"
                ], "Trimming dead air & hesitations for punchy, fast-paced retention")
                current_video = trimmed_video
        else:
            clips_to_assemble_dir = input_source
            if trim_silence:
                trimmed_clips_dir = temp_dir / "trimmed_clips"
                trimmed_clips_dir.mkdir(parents=True, exist_ok=True)
                sorted_clips = sorted(raw_clips, key=lambda p: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', p.stem)])
                for c in sorted_clips:
                    out_c = trimmed_clips_dir / c.name
                    run_step([
                        str(SCRIPT_DIR / "cut_dead_air.py"),
                        "-i", str(c),
                        "-o", str(out_c),
                        "-n", "-30.0",
                        "-s", "0.40",
                        "-p", "0.12"
                    ], f"Trimming dead air from {c.name}")
                clips_to_assemble_dir = trimmed_clips_dir

            # Track scene cut times for smart dialogue-aware zooms
            scene_cut_times = []
            ffprobe_exe = str(Path(sys.prefix) / "Scripts" / "ffprobe.exe") if (Path(sys.prefix) / "Scripts" / "ffprobe.exe").exists() else "ffprobe"
            assembled_files = sorted(list(clips_to_assemble_dir.glob("*.mp4")), key=lambda p: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', p.stem)])
            acc_t = 0.0
            for idx, af in enumerate(assembled_files):
                cmd = [ffprobe_exe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(af)]
                res = subprocess.run(cmd, capture_output=True, text=True)
                try:
                    dur = float(json.loads(res.stdout)["format"]["duration"])
                except Exception:
                    dur = 5.0
                if idx > 0:
                    acc_t = (acc_t + dur) - 0.22
                    scene_cut_times.append(round(acc_t, 2))
                else:
                    acc_t = dur

            current_video = temp_dir / "step1_assembled.mp4"
            run_step([
                str(SCRIPT_DIR / "apply_transitions.py"), "apply",
                "-i", str(clips_to_assemble_dir),
                "-o", str(current_video),
                "-t", cfg["transition"],
                "-d", "0.22",
                "--auto-sfx"
            ], f"Assembling {len(raw_clips)} clips with '{cfg['transition']}' transitions & auto-whooshes")
    else:
        current_video = input_source
        if trim_silence:
            trimmed_video = temp_dir / "step2_trimmed.mp4"
            run_step([
                str(SCRIPT_DIR / "cut_dead_air.py"),
                "-i", str(current_video),
                "-o", str(trimmed_video),
                "-n", "-30.0",
                "-s", "0.40",
                "-p", "0.12"
            ], "Trimming dead air & hesitations for punchy, fast-paced retention")
            current_video = trimmed_video

    if output_file is None:
        output_file = output_dir / f"ugc_master_{preset}.mp4"

    if add_zooms:
        zoomed_video = temp_dir / "step3_zoomed.mp4"
        zoom_args = [
            str(SCRIPT_DIR / "apply_keyframes.py"),
            "-i", str(current_video),
            "-o", str(zoomed_video),
            "-m", cfg["zoom_mode"],
            "-z", "1.18",
            "-a", "face"
        ]
        if 'scene_cut_times' in locals() and scene_cut_times:
            zoom_args.extend(["--scene-cuts", ",".join(map(str, scene_cut_times))])
            
        run_step(zoom_args, f"Applying '{cfg['zoom_mode']}' smart camera zooms (Face-Anchored & Scene-Synced)")
        current_video = zoomed_video

    ass_file = output_dir / f"{current_video.stem}_captions.ass"
    if add_captions:
        captioned_video = temp_dir / "step4_captioned.mp4"
        caption_args = [
            str(SCRIPT_DIR / "add_kinetic_captions.py"),
            "-i", str(current_video),
            "-o", str(captioned_video),
            "-s", cfg["caption_style"],
            "-w", "3"
        ]
        if custom_pinpoints:
            caption_args.extend(["-p", custom_pinpoints])
            
        run_step(caption_args, f"Transcribing audio & burning kinetic captions ({cfg['caption_style']} style)")
        current_video = captioned_video
        ass_file = output_dir / f"{current_video.stem}_captions.ass"

    if auto_graphics and ass_file.exists():
        scheduled_shapes = scan_transcript_for_creative_cues(ass_file)
        if scheduled_shapes:
            console.print(f"[bold green]Semantic Director:[/bold green] Detected [cyan]{len(scheduled_shapes)}[/cyan] moments requiring contextual motion graphics:")
            for s_idx, shape_info in enumerate(scheduled_shapes, 1):
                shape_video = temp_dir / f"step5_shape_{s_idx}.mp4"
                console.print(f"  * {shape_info['shape'].upper()} at [yellow]{shape_info['start']:.2f}s[/yellow] (Label: '{shape_info['label']}')")
                run_step([
                    str(SCRIPT_DIR / "apply_morphing_shapes.py"),
                    "-i", str(current_video),
                    "-o", str(shape_video),
                    "--shape", shape_info["shape"],
                    "--start", str(shape_info["start"]),
                    "--duration", str(shape_info["duration"]),
                    "--label", shape_info["label"],
                    "--color", cfg["shape_color"]
                ], f"Applying contextual '{shape_info['shape']}' overlay at {shape_info['start']:.2f}s")
                current_video = shape_video

    if add_sfx_layers:
        sfx_video = temp_dir / "step6_sfx.mp4"
        sfx_args = [
            str(SCRIPT_DIR / "add_sfx.py"), "apply",
            "-i", str(current_video),
            "-o", str(sfx_video),
            "-v", "0.35"
        ]
        
        # Build audio cues from scheduled shapes and narrative beats
        shape_cues = []
        if auto_graphics and 'scheduled_shapes' in locals() and scheduled_shapes:
            for s in scheduled_shapes:
                st = s["start"]
                sh = s["shape"]
                if sh == "bargraph":
                    shape_cues.append(f"{st:.2f}:power up")
                elif sh == "rectangle":
                    shape_cues.append(f"{st:.2f}:camera shutter")
                elif sh == "circular_motion":
                    shape_cues.append(f"{st:.2f}:ui beep")
                elif sh == "badge_callout":
                    shape_cues.append(f"{st:.2f}:slap")
                else:
                    shape_cues.append(f"{st:.2f}:whoosh fast")
                    
        if shape_cues:
            sfx_args.extend(["-c", ", ".join(shape_cues)])
        elif not ass_file.exists():
            sfx_args.extend(["-c", "1.0:whoosh, 3.5:click"])
            
        if ass_file.exists():
            sfx_args.extend(["--from-ass", str(ass_file)])
            
        run_step(sfx_args, "Layering sound effects and syncing pinpoint audio accents")
        current_video = sfx_video

    if add_bgm_track and Path("BM").exists() and list(Path("BM").glob("*.*")):
        bgm_video = temp_dir / "step7_bgm.mp4"
        run_step([
            str(SCRIPT_DIR / "add_bgm.py"), "mix",
            "-i", str(current_video),
            "-o", str(bgm_video),
            "-v", "0.18",
            "-d", "5.0"
        ], "Mixing BGM with dynamic voice-ducking compression")
        current_video = bgm_video

    if apply_grade:
        run_step([
            str(SCRIPT_DIR / "color_grade.py"), "apply",
            "-i", str(current_video),
            "-o", str(output_file),
            "-p", cfg["grade"]
        ], f"Applying '{cfg['grade']}' aesthetic color grading")
    else:
        import shutil
        shutil.copy2(current_video, output_file)

    try:
        import shutil
        shutil.rmtree(temp_dir)
    except Exception:
        pass

    console.print(Panel(
        f"[bold green]*** VIRAL UGC MASTER VIDEO PRODUCED SUCCESSFULLY! ***[/bold green]\n\n"
        f"Master Deliverable: [bold yellow]{output_file}[/bold yellow]\n"
        f"Preset Applied: [cyan]{preset.upper()}[/cyan] ({cfg['grade']} / {cfg['zoom_mode']} / {cfg['caption_style']})\n"
        f"Retention Engine: Full Hook-to-CTA pacing, semantic visual graphics, synced SFX & ducked BGM.",
        title="[bold green]COMPLETE[/bold green]"
    ))

if __name__ == "__main__":
    app()
