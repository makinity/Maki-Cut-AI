#!/usr/bin/env python3
"""
SFX (Sound Effects) Layering and Auto-Sync Tool for UGC Videos.
Pulls from the curated SFX/ library, maps sound effects to visual events/pinpoints,
and mixes them at calibrated volume levels with lossless video passthrough.
"""

import sys
import os
import re
import json
import math
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import typer
from rich.console import Console
from rich.table import Table
from pydub import AudioSegment

app = typer.Typer(help="Manage and mix SFX into videos for high-energy UGC pacing.")
console = Console()

SFX_DIR = Path("SFX")

CATEGORY_MAPPINGS = {
    "whoosh": ["whoosh", "buzz - whoosh", "data_whoosh", "whoosh fast", "whoosh main", "whoosh 2", "whoosh 3", "whoosh 6"],
    "click": ["click", "shutter", "switch click", "ui beep", "camera shutter", "typewriter"],
    "riser": ["riser", "sharp riser", "riser short", "suspense"],
    "impact": ["slap", "splash", "power up", "scene change"],
    "funny": ["nope", "quack", "quick fart", "sad violin", "toy duck", "ugh", "cartoon throw away"],
}

def get_ffmpeg_paths() -> Tuple[str, str]:
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def catalog_sfx_files() -> Dict[str, Dict[str, Any]]:
    """Scan SFX/ folder and categorize available audio clips."""
    catalog = {}
    if not SFX_DIR.exists():
        return catalog
        
    for p in SFX_DIR.glob("*.*"):
        if p.suffix.lower() in [".mp3", ".wav", ".aac", ".ogg", ".m4a"]:
            name_lower = p.stem.lower()
            category = "general"
            for cat, keywords in CATEGORY_MAPPINGS.items():
                if any(kw in name_lower for kw in keywords):
                    category = cat
                    break
                    
            catalog[p.name] = {
                "path": p,
                "stem": p.stem,
                "category": category,
            }
    return catalog

def find_best_sfx_match(query: str, catalog: Dict[str, Dict[str, Any]]) -> Optional[Path]:
    """Find SFX file by exact filename, partial match, or category tag."""
    q = query.strip().lower()
    
    # 1. Exact filename match
    for fname, data in catalog.items():
        if fname.lower() == q or data["stem"].lower() == q:
            return data["path"]
            
    # 2. Category query: return first or random item from category
    matching_in_category = [d["path"] for d in catalog.values() if d["category"] == q]
    if matching_in_category:
        return matching_in_category[0]
        
    # 3. Substring match
    for fname, data in catalog.items():
        if q in fname.lower():
            return data["path"]
            
    return None

@app.command(name="list")
def list_sfx():
    """List all available sound effects in the SFX/ directory grouped by category."""
    catalog = catalog_sfx_files()
    if not catalog:
        console.print("[bold red]No SFX files found in SFX/ folder![/bold red]")
        return
        
    table = Table(title="Curated SFX Library (Makinity Cut)")
    table.add_column("Filename", style="cyan", no_wrap=False)
    table.add_column("Category", style="green")
    table.add_column("Best Used For", style="yellow")
    
    usage_hints = {
        "whoosh": "Transitions, morphing shapes, scene cuts, text slide-ins",
        "click": "Kinetic text pop-ins, context pinpoints, button presses",
        "riser": "Build-ups, suspense hooks, questions, dramatic storytelling",
        "impact": "Punchy reveals, big numbers, scene shifts, meme slaps",
        "funny": "Mistakes, bloopers, sarcastic moments, disbelief",
        "general": "Atmospheric accent",
    }
    
    for fname, data in sorted(catalog.items(), key=lambda x: (x[1]["category"], x[0])):
        cat = data["category"]
        table.add_row(fname, cat.upper(), usage_hints.get(cat, ""))
        
    console.print(table)
    console.print(f"[bold green]Total: {len(catalog)} audio assets ready to use.[/bold green]")

@app.command(name="apply")
def apply_sfx(
    input_file: Path = typer.Option(..., "--input", "-i", help="Path to video (in Input/ or Output/)"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Target output video path"),
    cues: Optional[str] = typer.Option(None, "--cues", "-c", help="Cues format: 'timestamp:sfx_name_or_cat, ...' e.g. '1.5:whoosh, 3.2:click, 5.0:slap'"),
    from_ass: Optional[Path] = typer.Option(None, "--from-ass", help="Automatically sync SFX to pinpoint events in an .ass subtitle file"),
    volume: float = typer.Option(0.35, "--volume", "-v", help="Relative volume of SFX (0.1 to 1.0, default 0.35)")
):
    """
    Mixes synchronized SFX into video audio track with precision timing.
    """
    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file '{input_file}' not found![/bold red]")
        raise typer.Exit(1)
        
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if output_file is None:
        output_file = output_dir / f"{input_file.stem}_with_sfx.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    catalog = catalog_sfx_files()
    if not catalog:
        console.print("[bold red]SFX directory is empty![/bold red]")
        raise typer.Exit(1)

    cue_list: List[Tuple[float, Path]] = []
    
    # 1. Parse manual cues if provided
    if cues:
        items = [x.strip() for x in cues.split(",") if x.strip()]
        for item in items:
            if ":" in item:
                time_str, sfx_query = item.split(":", 1)
                try:
                    t_sec = float(time_str.strip())
                    matched_path = find_best_sfx_match(sfx_query, catalog)
                    if matched_path:
                        cue_list.append((t_sec, matched_path))
                        console.print(f"Queued SFX at [yellow]{t_sec:.2f}s[/yellow]: [cyan]{matched_path.name}[/cyan]")
                    else:
                        console.print(f"[red]Warning: No SFX matched '{sfx_query}'[/red]")
                except ValueError:
                    console.print(f"[red]Invalid timestamp: {time_str}[/red]")

    # 2. Parse from ASS subtitle if requested
    if from_ass and from_ass.exists():
        console.print(f"[cyan]Parsing pinpoint events from subtitle: {from_ass.name}...[/cyan]")
        with open(from_ass, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("Dialogue:"):
                    if "\\t(0,120,\\fscx125" in line or "\\c&H0014FF39&" in line:
                        parts = line.split(",", 9)
                        if len(parts) >= 10:
                            start_str = parts[1]
                            h, m, s = start_str.split(":")
                            start_sec = int(h) * 3600 + int(m) * 60 + float(s)
                            click_sfx = find_best_sfx_match("click", catalog)
                            if click_sfx:
                                cue_list.append((start_sec, click_sfx))
                                console.print(f"Auto-synced pinpoint click at [yellow]{start_sec:.2f}s[/yellow]")

    if not cue_list:
        console.print("[yellow]No SFX cues specified. Use --cues '1.5:whoosh, 3.0:click' or --from-ass[/yellow]")
        return

    # 3. Extract and load video audio
    console.print(f"[bold green]Loading video audio stream...[/bold green]")
    temp_wav = output_dir / f"temp_{input_file.stem}_audio.wav"
    temp_mixed_wav = output_dir / f"temp_{input_file.stem}_mixed.wav"
    
    extract_cmd = [ffmpeg_exe, "-y", "-i", str(input_file), "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", str(temp_wav)]
    subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    base_audio = AudioSegment.from_file(str(temp_wav))
    gain_db = 20 * math.log10(max(0.01, volume))
    
    console.print(f"Mixing [bold cyan]{len(cue_list)}[/bold cyan] SFX triggers into audio timeline...")
    for t_sec, sfx_path in cue_list:
        pos_ms = int(t_sec * 1000)
        if pos_ms < len(base_audio):
            sfx_clip = AudioSegment.from_file(str(sfx_path))
            sfx_clip = sfx_clip.apply_gain(gain_db)
            base_audio = base_audio.overlay(sfx_clip, position=pos_ms)
            
    base_audio.export(str(temp_mixed_wav), format="wav")
    console.print("[green]SFX audio layer successfully mixed and balanced.[/green]")

    # 4. Mux new audio back into video losslessly without re-encoding video stream
    console.print(f"[cyan]Muxing balanced audio into output video...[/cyan]")
    mux_cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(input_file),
        "-i", str(temp_mixed_wav),
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_file)
    ]
    subprocess.run(mux_cmd, check=True)
    
    if temp_wav.exists():
        temp_wav.unlink()
    if temp_mixed_wav.exists():
        temp_mixed_wav.unlink()
        
    console.print(f"\n[bold green]Success![/bold green] SFX added to video: [bold]{output_file}[/bold]")

if __name__ == "__main__":
    app()

