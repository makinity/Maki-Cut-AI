#!/usr/bin/env python3
"""
Color Grading & Aesthetic Stylization Engine for UGC Videos.
Applies curated visual looks (Vibrant Pop, Warm Golden, Cinematic Teal/Orange, Clean Bright, etc.)
or custom color balance, saturation, temperature, and vignette to match user preference.
"""

import sys
import os
import math
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Apply color grading and cinematic looks to videos.")
console = Console()

PRESET_GRADES = {
    "vibrant_pop": {
        "description": "High-energy punchy look with boosted saturation and crisp contrast (TikTok/Shorts standard).",
        "eq": "contrast=1.12:brightness=0.02:saturation=1.28:gamma=1.04",
        "colorbalance": "rm=0.04:gm=0.01:bm=-0.03:rh=0.03:bh=-0.03",
        "vignette": 0.0
    },
    "warm_golden": {
        "description": "Golden hour glow with rich warm midtones and flattering skin tones.",
        "eq": "contrast=1.08:brightness=0.02:saturation=1.15:gamma=1.05",
        "colorbalance": "rm=0.08:gm=0.02:bm=-0.08:rh=0.06:gh=0.02:bh=-0.06",
        "vignette": 0.20
    },
    "teal_and_orange": {
        "description": "Blockbuster cinematic split-toning with cool shadows and warm highlights.",
        "eq": "contrast=1.16:brightness=0.01:saturation=1.18:gamma=1.02",
        "colorbalance": "rs=-0.07:gs=0.01:bs=0.08:rh=0.08:gh=0.02:bh=-0.08",
        "vignette": 0.25
    },
    "clean_bright": {
        "description": "High-key commercial aesthetic, crisp true whites, lifted shadows, natural skin tones.",
        "eq": "contrast=1.06:brightness=0.04:saturation=1.08:gamma=1.08",
        "colorbalance": "rs=0.0:gs=0.0:bs=0.0",
        "vignette": 0.0
    },
    "moody_dark": {
        "description": "Modern tech aesthetic with desaturated cool highlights and deep rich blacks.",
        "eq": "contrast=1.22:brightness=-0.03:saturation=0.88:gamma=0.96",
        "colorbalance": "rs=0.02:gs=0.0:bs=0.06:rh=-0.04:gh=0.0:bh=0.05",
        "vignette": 0.35
    },
    "retro_film": {
        "description": "90s nostalgic film look with lifted faded blacks, amber tints, and subtle vignette.",
        "eq": "contrast=1.08:brightness=0.03:saturation=1.05:gamma=1.06",
        "colorbalance": "rs=0.04:gs=0.02:bs=-0.03:rm=0.06:gm=0.02:bm=-0.05",
        "vignette": 0.30
    },
    "bw_noir": {
        "description": "High-contrast monochrome with punchy highlights and deep shadows.",
        "eq": "contrast=1.25:brightness=0.0:saturation=0.0:gamma=0.98",
        "colorbalance": "",
        "vignette": 0.20
    }
}

def get_ffmpeg_paths() -> Tuple[str, str]:
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

@app.command(name="list")
def list_presets():
    """List all available color grading presets and descriptions."""
    table = Table(title="Available Color Grading Presets (Makinity Cut)")
    table.add_column("Preset Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="yellow")
    
    for name, data in PRESET_GRADES.items():
        table.add_row(name, data["description"])
        
    console.print(table)

@app.command(name="apply")
def apply_grade(
    input_file: Path = typer.Option(..., "--input", "-i", help="Path to video (in Input/ or Output/)"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Target output video path"),
    preset: str = typer.Option("vibrant_pop", "--preset", "-p", help="Color preset: vibrant_pop, warm_golden, teal_and_orange, clean_bright, moody_dark, retro_film, bw_noir"),
    brightness: float = typer.Option(0.0, "--brightness", "-b", help="Brightness adjustment (-0.5 to 0.5)"),
    contrast: float = typer.Option(1.0, "--contrast", "-c", help="Contrast multiplier (0.5 to 2.0)"),
    saturation: float = typer.Option(1.0, "--saturation", "-s", help="Saturation multiplier (0.0 to 2.5)"),
    temperature: float = typer.Option(0.0, "--temp", "-t", help="Color temperature: negative=cool blue, positive=warm amber (-1.0 to 1.0)"),
    vignette: float = typer.Option(0.0, "--vignette", "-v", help="Vignette strength (0.0 = none to 1.0 = heavy)"),
    lut: Optional[Path] = typer.Option(None, "--lut", help="Path to external .cube 3D LUT file")
):
    """
    Applies cinematic color grading or custom visual aesthetics to video.
    """
    ffmpeg_exe, _ = get_ffmpeg_paths()
    
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file '{input_file}' not found![/bold red]")
        raise typer.Exit(1)
        
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if output_file is None:
        output_file = output_dir / f"{input_file.stem}_{preset}.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    filters = []
    
    # 1. 3D LUT if provided
    if lut and lut.exists():
        console.print(f"[cyan]Applying 3D LUT file: {lut.name}...[/cyan]")
        lut_path = str(lut.as_posix())
        filters.append(f"lut3d='{lut_path}'")
        
    # 2. Preset Base Grading
    preset_data = PRESET_GRADES.get(preset.lower(), PRESET_GRADES["vibrant_pop"])
    console.print(f"[bold green]Applying Preset:[/bold green] [bold cyan]{preset.upper()}[/bold cyan] — {preset_data['description']}")
    
    if preset_data.get("eq"):
        filters.append(f"eq={preset_data['eq']}")
    if preset_data.get("colorbalance"):
        filters.append(f"colorbalance={preset_data['colorbalance']}")
        
    # 3. Custom Adjustments (Overrides / Tweaks)
    custom_eq_parts = []
    if brightness != 0.0:
        custom_eq_parts.append(f"brightness={brightness:.3f}")
    if contrast != 1.0:
        custom_eq_parts.append(f"contrast={contrast:.3f}")
    if saturation != 1.0:
        custom_eq_parts.append(f"saturation={saturation:.3f}")
        
    if custom_eq_parts:
        filters.append(f"eq={':'.join(custom_eq_parts)}")
        
    # 4. Temperature Shift
    if temperature != 0.0:
        r_shift = temperature * 0.10
        b_shift = -temperature * 0.10
        filters.append(f"colorbalance=rs={r_shift:.3f}:bs={b_shift:.3f}:rm={r_shift*1.2:.3f}:bm={b_shift*1.2:.3f}")
        
    # 5. Vignette
    final_vignette = max(vignette, preset_data.get("vignette", 0.0))
    if final_vignette > 0.0:
        vig_angle = f"PI/{max(2.5, 7.0 - final_vignette * 4.5):.2f}"
        filters.append(f"vignette={vig_angle}")
        
    vf_string = ",".join(filters) if filters else "null"
    
    console.print(f"[cyan]Rendering color graded output via FFmpeg...[/cyan]")
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(input_file),
        "-vf", vf_string,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "copy",
        str(output_file)
    ]
    
    subprocess.run(cmd, check=True)
    console.print(f"\n[bold green]Success![/bold green] Color graded video saved to: [bold]{output_file}[/bold]")

if __name__ == "__main__":
    app()

