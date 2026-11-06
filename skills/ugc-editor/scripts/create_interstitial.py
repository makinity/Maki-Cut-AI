#!/usr/bin/env python3
"""
Listicle Section Title Interstitial Generator for UGC Videos.
Inspired by Study 3 (CapCut 3 Viral Video Editing Tips).
Generates high-energy 1.2s-1.5s full-screen chapter title cards ('TIP #1: THE 3-SECOND HOOK',
'MISTAKE #2: SLOW PACING') with slam zoom physics, tilted neon badge headers,
angled caution/cyber patterns, radial dark vignettes, and synchronized impact SFX.
Supports both standalone clip creation ('generate') and in-place timeline splicing ('insert').
"""

import sys
import os
import math
import subprocess
import json
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
import typer
from rich.console import Console
from PIL import Image, ImageDraw, ImageFont, ImageFilter

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(help="Generate and splice listicle section title interstitials and chapter cards.")
console = Console()

INTERSTITIAL_PALETTES = {
    "yellow_punch": {
        "badge_bg": (255, 230, 0, 255),     # Electric Yellow
        "badge_text": (0, 0, 0, 255),        # Black
        "headline": (255, 255, 255, 255),   # White
        "accent": (255, 230, 0, 255),       # Yellow
        "sub": (200, 205, 215, 255),        # Light Silver
        "bg_top": (16, 18, 24, 255),        # Dark Cyber
        "bg_bottom": (8, 9, 12, 255),
    },
    "neon_cyan": {
        "badge_bg": (0, 229, 255, 255),     # Neon Cyan
        "badge_text": (0, 0, 0, 255),
        "headline": (255, 255, 255, 255),
        "accent": (0, 229, 255, 255),
        "sub": (180, 220, 230, 255),
        "bg_top": (12, 20, 28, 255),
        "bg_bottom": (6, 10, 14, 255),
    },
    "alert_red": {
        "badge_bg": (255, 35, 45, 255),     # Alert Red
        "badge_text": (255, 255, 255, 255),
        "headline": (255, 255, 255, 255),
        "accent": (255, 45, 55, 255),
        "sub": (240, 190, 195, 255),
        "bg_top": (24, 12, 14, 255),
        "bg_bottom": (12, 6, 7, 255),
    },
    "gold_luxury": {
        "badge_bg": (255, 215, 0, 255),     # Gold
        "badge_text": (18, 16, 12, 255),
        "headline": (255, 245, 220, 255),
        "accent": (255, 215, 0, 255),
        "sub": (210, 195, 170, 255),
        "bg_top": (22, 18, 14, 255),
        "bg_bottom": (11, 9, 7, 255),
    }
}

def get_ffmpeg_paths() -> Tuple[str, str]:
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def get_video_specs(video_path: Path, ffprobe_exe: str) -> Tuple[int, int, float, float]:
    cmd = [
        ffprobe_exe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration",
        "-of", "json",
        str(video_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    info = json.loads(res.stdout)["streams"][0]
    w = int(info["width"])
    h = int(info["height"])
    fps_parts = info["r_frame_rate"].split('/')
    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
    duration = float(info.get("duration", 0.0))
    if duration == 0.0:
        cmd_fmt = [ffprobe_exe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video_path)]
        res_fmt = subprocess.run(cmd_fmt, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        duration = float(json.loads(res_fmt.stdout).get("format", {}).get("duration", 10.0))
    return w, h, fps, duration

def get_best_font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    font_paths = [
        "fonts/ArchivoBlack-Regular.ttf" if bold else "fonts/Archivo-Variable.ttf",
        "fonts/Roboto-Bold.ttf" if bold else "fonts/Roboto.ttf",
        "fonts/Montserrat.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()

def ease_out_bounce(t: float) -> float:
    """Juicy impact bounce for title slam."""
    if t < 0.6:
        # Rapid slam from 1.35x down to 0.95x
        p = t / 0.6
        return 1.35 - 0.40 * (1.0 - math.pow(1.0 - p, 3))
    else:
        # Subtle rebound to 1.0x
        p = (t - 0.6) / 0.4
        return 0.95 + 0.05 * math.sin(p * math.pi * 0.5)

def create_static_interstitial_bg(w: int, h: int, palette: dict) -> Image.Image:
    """Pre-renders static textured gradient background with stripes and vignette."""
    bg = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    bg_draw = ImageDraw.Draw(bg)
    
    top_c = palette["bg_top"]
    bot_c = palette["bg_bottom"]
    for y_step in range(0, h, 8):
        factor = y_step / float(h)
        curr_r = int(top_c[0] * (1.0 - factor) + bot_c[0] * factor)
        curr_g = int(top_c[1] * (1.0 - factor) + bot_c[1] * factor)
        curr_b = int(top_c[2] * (1.0 - factor) + bot_c[2] * factor)
        bg_draw.rectangle([0, y_step, w, min(h, y_step + 8)], fill=(curr_r, curr_g, curr_b, 255))
        
    # Stripes
    stripe_w = int(w * 0.035)
    stripe_spacing = int(w * 0.09)
    accent_rgb = palette["accent"]
    stripe_alpha = 18
    for sx in range(-h, w + h, stripe_spacing):
        pts = [
            (sx, 0),
            (sx + stripe_w, 0),
            (sx + stripe_w + int(h * 0.45), h),
            (sx + int(h * 0.45), h)
        ]
        bg_draw.polygon(pts, fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], stripe_alpha))
        
    # Vignette
    vignette = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    cx, cy = w // 2, h // 2
    max_radius = math.hypot(cx, cy)
    for r_step in range(int(max_radius * 0.55), int(max_radius), 24):
        p_v = (r_step - max_radius * 0.55) / (max_radius * 0.45)
        alpha = int(190 * p_v)
        v_draw.ellipse([cx - r_step, cy - r_step, cx + r_step, cy + r_step], outline=(0, 0, 0, alpha), width=24)
    bg.alpha_composite(vignette)
    return bg

def render_interstitial_frame(
    progress: float,
    w: int,
    h: int,
    tag: str,
    headline: str,
    sub: str,
    step_indicator: str,
    palette_name: str,
    base_bg: Image.Image,
    angle_deg: float = -4.0
) -> Image.Image:
    """Renders a single frame of a full-screen interstitial chapter card."""
    pal = INTERSTITIAL_PALETTES.get(palette_name.lower(), INTERSTITIAL_PALETTES["yellow_punch"])
    bg = base_bg.copy()
    cx, cy = w // 2, h // 2
    
    # Animated Content Layer (Slam Zoom & Tilt)
    content_canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(content_canvas)
    
    # Calculate scale
    if progress < 0.22:
        scale = ease_out_bounce(progress / 0.22)
    elif progress > 0.88:
        # Quick fade-out zoom
        t_out = (progress - 0.88) / 0.12
        scale = 1.0 + 0.15 * t_out
    else:
        # Subtle slow cinematic creeping zoom
        t_mid = (progress - 0.22) / 0.66
        scale = 1.0 + 0.03 * t_mid
        
    # Tag Badge (e.g. 'TIP #1' or 'MISTAKE #2')
    tag_text = tag.upper()
    tag_font_size = max(18, int(h * 0.032 * scale))
    tag_font = get_best_font(tag_font_size, bold=True)
    t_bbox = cdraw.textbbox((0, 0), tag_text, font=tag_font)
    t_w = t_bbox[2] - t_bbox[0]
    t_h = t_bbox[3] - t_bbox[1]
    
    tag_pad_x = int(32 * scale)
    tag_pad_y = int(14 * scale)
    tag_bw = t_w + tag_pad_x * 2
    tag_bh = t_h + tag_pad_y * 2
    
    tag_cy = int(h * 0.40)
    tag_x0 = cx - tag_bw // 2
    tag_y0 = tag_cy - tag_bh // 2
    tag_x1 = cx + tag_bw // 2
    tag_y1 = tag_cy + tag_bh // 2
    
    # Drop shadow
    cdraw.rounded_rectangle([tag_x0 + 4, tag_y0 + 4, tag_x1 + 4, tag_y1 + 4], radius=tag_bh // 2, fill=(0, 0, 0, 180))
    # Badge Pill
    cdraw.rounded_rectangle([tag_x0, tag_y0, tag_x1, tag_y1], radius=tag_bh // 2, fill=pal["badge_bg"])
    cdraw.text((cx, tag_cy), tag_text, font=tag_font, fill=pal["badge_text"], anchor="mm")
    
    # 5. Giant Impact Headline (multi-line supported)
    headline_text = headline.upper()
    hl_font_size = max(24, int(h * 0.056 * scale))
    hl_font = get_best_font(hl_font_size, bold=True)
    
    # Word wrap if text is long
    hl_words = headline_text.split()
    hl_lines = []
    curr_line = []
    max_line_w = int(w * 0.85)
    
    for word in hl_words:
        test_line = " ".join(curr_line + [word])
        w_bbox = cdraw.textbbox((0, 0), test_line, font=hl_font)
        if (w_bbox[2] - w_bbox[0]) <= max_line_w:
            curr_line.append(word)
        else:
            if curr_line:
                hl_lines.append(" ".join(curr_line))
            curr_line = [word]
    if curr_line:
        hl_lines.append(" ".join(curr_line))
        
    line_h = int(hl_font_size * 1.22)
    total_hl_h = len(hl_lines) * line_h
    start_hl_y = int(h * 0.48)
    
    for l_idx, line_str in enumerate(hl_lines):
        ly = start_hl_y + l_idx * line_h
        # Heavy drop shadow
        cdraw.text((cx + 5, ly + 5), line_str, font=hl_font, fill=(0, 0, 0, 240), anchor="mm")
        cdraw.text((cx, ly), line_str, font=hl_font, fill=pal["headline"], anchor="mm")
        
    # 6. Subtitle / One-Line Takeaway
    if sub:
        sub_font_size = max(14, int(h * 0.022 * scale))
        sub_font = get_best_font(sub_font_size, bold=False)
        sub_y = start_hl_y + total_hl_h + int(18 * scale)
        cdraw.text((cx + 2, sub_y + 2), sub, font=sub_font, fill=(0, 0, 0, 200), anchor="mm")
        cdraw.text((cx, sub_y), sub, font=sub_font, fill=pal["sub"], anchor="mm")
        
    # 7. Step Counter / Dots at bottom
    if step_indicator:
        step_font_size = max(12, int(h * 0.020))
        step_font = get_best_font(step_font_size, bold=True)
        step_y = int(h * 0.88)
        cdraw.text((cx, step_y), step_indicator.upper(), font=step_font, fill=pal["accent"], anchor="mm")
        
    # Apply angle rotation if requested (CapCut listicle tilted style!)
    if abs(angle_deg) > 0.1:
        rotated_content = content_canvas.rotate(-angle_deg, resample=Image.BICUBIC, center=(cx, cy))
        bg.alpha_composite(rotated_content)
    else:
        bg.alpha_composite(content_canvas)
        
    return bg

@app.command()
def generate(
    output_file: Path = typer.Option(..., "--output", "-o", help="Target output interstitial .mp4 path"),
    tag: str = typer.Option("TIP #1", "--tag", "-t", help="Numbered badge text (e.g. 'TIP #1', 'MISTAKE #2', 'STEP 03')"),
    headline: str = typer.Option("THE 3-SECOND HOOK", "--headline", "-hl", help="Main impact headline (e.g. 'THE 3-SECOND HOOK', 'ZERO DEAD AIR')"),
    sub: str = typer.Option("Never let the viewer look away", "--sub", help="Subtitle or takeaway 1-liner"),
    step: str = typer.Option("STEP 1 OF 3", "--step", help="Bottom step counter / indicator (e.g. 'STEP 1 OF 3')"),
    duration: float = typer.Option(1.4, "--duration", "-d", help="Interstitial duration in seconds (default: 1.4s)"),
    theme: str = typer.Option("yellow_punch", "--theme", help="Color theme: 'yellow_punch', 'neon_cyan', 'alert_red', 'gold_luxury'"),
    angle: float = typer.Option(-4.0, "--angle", help="Tilt angle in degrees (default: -4.0)"),
    width: int = typer.Option(1080, "--width", "-w", help="Output video width (default: 1080)"),
    height: int = typer.Option(1920, "--height", "-h", help="Output video height (default: 1920)"),
    fps: int = typer.Option(30, "--fps", help="Output frame rate (default: 30)"),
    sfx: bool = typer.Option(True, "--sfx/--no-sfx", help="Mix impact sound effect")
):
    """
    Generates a standalone full-screen listicle section title interstitial video clip.
    """
    ffmpeg_exe, _ = get_ffmpeg_paths()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    total_frames = max(1, int(duration * fps))
    console.print(f"[bold cyan]Generating {duration:.2f}s Listicle Interstitial:[/bold cyan] {output_file.name}")
    console.print(f"  • Tag: [bold]{tag}[/bold] | Headline: [bold]{headline}[/bold]")
    console.print(f"  • Resolution: {width}x{height} @ {fps} fps ({total_frames} frames)")
    
    temp_video = output_file.parent / f"temp_interstitial_{output_file.stem}.mp4"
    
    # 1. Pipe frames to FFmpeg
    pal = INTERSTITIAL_PALETTES.get(theme.lower(), INTERSTITIAL_PALETTES["yellow_punch"])
    base_bg = create_static_interstitial_bg(width, height, pal)
    
    pipe_cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "rgba",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        "-r", str(fps),
        str(temp_video)
    ]
    
    proc = subprocess.Popen(pipe_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for f_idx in range(total_frames):
        p = f_idx / float(total_frames)
        frame_img = render_interstitial_frame(
            progress=p,
            w=width,
            h=height,
            tag=tag,
            headline=headline,
            sub=sub,
            step_indicator=step,
            palette_name=theme,
            base_bg=base_bg,
            angle_deg=angle
        )
        proc.stdin.write(frame_img.tobytes())
        
    proc.stdin.close()
    proc.wait()
    console.print("[green]Video frames rendered.[/green]")
    
    # 2. Add Audio / SFX
    sfx_cand = None
    if sfx:
        for c in ["SFX/SLAP SFX.mp3", "SFX/Buzz - Whoosh.wav", "SFX/Riser Short.wav", "SFX/whoosh-6316.mp3"]:
            if os.path.exists(c):
                sfx_cand = c
                break
                
    if sfx_cand:
        console.print(f"[cyan]Layering impact sound effect: [bold]{sfx_cand}[/bold]...[/cyan]")
        audio_cmd = [
            ffmpeg_exe,
            "-y",
            "-i", str(temp_video),
            "-i", str(sfx_cand),
            "-filter_complex", f"[1:a]volume=0.65,apad=pad_dur={duration}[a_padded];[a_padded]atrim=0:{duration}[a_out]",
            "-map", "0:v",
            "-map", "[a_out]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            str(output_file)
        ]
    else:
        # Silent audio track for broadcast compatibility
        audio_cmd = [
            ffmpeg_exe,
            "-y",
            "-i", str(temp_video),
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_file)
        ]
        
    subprocess.run(audio_cmd, check=True)
    if temp_video.exists():
        temp_video.unlink()
        
    console.print(f"[bold green]Success![/bold green] Section title interstitial saved to: [bold]{output_file}[/bold]")

@app.command()
def insert(
    input_file: Path = typer.Option(..., "--input", "-i", help="Main video file path"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Final output spliced video path"),
    at_time: float = typer.Option(..., "--at", help="Timestamp in seconds where interstitial is inserted"),
    tag: str = typer.Option("TIP #1", "--tag", "-t", help="Numbered badge text (e.g. 'TIP #1')"),
    headline: str = typer.Option("THE 3-SECOND HOOK", "--headline", "-hl", help="Main impact headline"),
    sub: str = typer.Option("Never let the viewer look away", "--sub", help="Subtitle or takeaway 1-liner"),
    step: str = typer.Option("STEP 1 OF 3", "--step", help="Bottom step counter / indicator"),
    duration: float = typer.Option(1.4, "--duration", "-d", help="Interstitial duration in seconds (default: 1.4s)"),
    theme: str = typer.Option("yellow_punch", "--theme", help="Color theme: 'yellow_punch', 'neon_cyan', 'alert_red', 'gold_luxury'"),
    angle: float = typer.Option(-4.0, "--angle", help="Tilt angle in degrees (default: -4.0)"),
    sfx: bool = typer.Option(True, "--sfx/--no-sfx", help="Mix impact sound effect")
):
    """
    Splices a full-screen section title interstitial directly into an existing video at a given timestamp.
    """
    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file '{input_file}' not found![/bold red]")
        raise typer.Exit(1)
        
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_file is None:
        output_file = output_dir / f"{input_file.stem}_with_chapter_{at_time:.1f}s.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    w, h, fps, total_dur = get_video_specs(input_file, ffprobe_exe)
    if at_time <= 0 or at_time >= total_dur:
        console.print(f"[bold red]Error: Insertion time {at_time:.2f}s is out of video range (0 - {total_dur:.2f}s)![/bold red]")
        raise typer.Exit(1)
        
    console.print(f"[bold cyan]Splicing interstitial at {at_time:.2f}s into:[/bold cyan] {input_file.name}")
    interstitial_temp = output_dir / f"temp_inter_{input_file.stem}.mp4"
    
    # 1. Generate interstitial clip matching input specs
    generate(
        output_file=interstitial_temp,
        tag=tag,
        headline=headline,
        sub=sub,
        step=step,
        duration=duration,
        theme=theme,
        angle=angle,
        width=w,
        height=h,
        fps=int(round(fps)),
        sfx=sfx
    )
    
    # 2. Slice input into Part A (0 to at_time) and Part B (at_time to end), then concatenate
    console.print("[cyan]Splicing Part A, Interstitial, and Part B together...[/cyan]")
    concat_filter = (
        f"[0:v]trim=start=0:end={at_time:.3f},setpts=PTS-STARTPTS,scale={w}:{h},setsar=1[v0];"
        f"[0:a]atrim=start=0:end={at_time:.3f},asetpts=PTS-STARTPTS,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a0];"
        f"[1:v]scale={w}:{h},setsar=1[v1];"
        f"[1:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a1];"
        f"[0:v]trim=start={at_time:.3f},setpts=PTS-STARTPTS,scale={w}:{h},setsar=1[v2];"
        f"[0:a]atrim=start={at_time:.3f},asetpts=PTS-STARTPTS,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a2];"
        f"[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[outv][outa]"
    )
    
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(input_file),
        "-i", str(interstitial_temp),
        "-filter_complex", concat_filter,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-ac", "2",
        str(output_file)
    ]
    
    subprocess.run(cmd, check=True)
    if interstitial_temp.exists():
        interstitial_temp.unlink()
        
    console.print(f"\n[bold green]Success![/bold green] Spliced video with chapter interstitial saved to: [bold]{output_file}[/bold]")

if __name__ == "__main__":
    app()
