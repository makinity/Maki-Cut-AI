#!/usr/bin/env python3
"""
Trust Seal & Risk-Reversal Guarantee Badge Generator for UGC Videos.
Inspired by Study 2 (Pavra Red Light Therapy UGC & direct-response e-commerce ads).
Renders animated circular medallions, 90-Day Money-Back Guarantee badges,
5-star review seals, dermatologist-approved certs, with specular light sweeps,
gentle rotation/pulse, and synchronized SFX.
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

app = typer.Typer(help="Add animated guarantee seals, trust badges, and risk-reversal rosettes.")
console = Console()

SEAL_THEMES = {
    "gold_luxury": {
        "primary": (255, 215, 0, 255),      # Gold
        "secondary": (184, 134, 11, 255),  # Dark Goldenrod
        "core_bg": (18, 16, 12, 240),      # Dark Charcoal / Gold tint
        "text": (255, 240, 180, 255),      # Light Gold text
        "accent": (255, 255, 255, 255),    # Specular white
        "ribbon": (180, 20, 20, 255),      # Deep Crimson ribbon
    },
    "medical_clean": {
        "primary": (0, 190, 230, 255),     # Medical Cyan
        "secondary": (0, 120, 180, 255),   # Deep Blue
        "core_bg": (10, 20, 28, 240),      # Dark Blue-Grey
        "text": (240, 250, 255, 255),      # White
        "accent": (255, 255, 255, 255),
        "ribbon": (0, 140, 200, 255),
    },
    "emerald_trust": {
        "primary": (0, 230, 118, 255),     # Vibrant Emerald
        "secondary": (0, 150, 80, 255),    # Deep Green
        "core_bg": (10, 24, 16, 240),      # Dark Forest
        "text": (230, 255, 240, 255),
        "accent": (255, 255, 255, 255),
        "ribbon": (0, 160, 90, 255),
    },
    "crimson_seal": {
        "primary": (255, 50, 60, 255),     # Bold Red
        "secondary": (180, 15, 25, 255),   # Crimson
        "core_bg": (22, 10, 12, 240),      # Dark Wine
        "text": (255, 255, 255, 255),
        "accent": (255, 220, 80, 255),     # Gold star accent
        "ribbon": (200, 25, 35, 255),
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

def ease_out_back(t: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * math.pow(t - 1.0, 3) + c1 * math.pow(t - 1.0, 2)

def draw_star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r_out: float, r_in: float, fill_color: tuple) -> None:
    """Draws a 5-pointed star."""
    points = []
    angle_step = math.pi / 5.0
    start_angle = -math.pi / 2.0
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        angle = start_angle + i * angle_step
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=fill_color)

def render_scalloped_rosette(
    radius: int,
    num_teeth: int = 24,
    tooth_depth: float = 6.0,
    rotation_deg: float = 0.0
) -> List[Tuple[float, float]]:
    """Calculates polygon points for a scalloped rosette edge."""
    points = []
    total_steps = num_teeth * 2
    step_angle = 2.0 * math.pi / total_steps
    base_rot = math.radians(rotation_deg)
    
    for i in range(total_steps):
        r = radius if i % 2 == 0 else (radius - tooth_depth)
        theta = base_rot + i * step_angle
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        points.append((x, y))
    return points

def draw_circular_text(
    img: Image.Image,
    text: str,
    cx: int,
    cy: int,
    radius: float,
    start_angle_deg: float,
    span_deg: float,
    font: ImageFont.ImageFont,
    fill_color: tuple,
    flip: bool = False
) -> None:
    """Renders text characters along a circular arc."""
    if not text:
        return
        
    chars = list(text)
    n = len(chars)
    if n == 0:
        return
        
    angle_step = span_deg / max(1, n - 1) if n > 1 else 0
    
    for i, ch in enumerate(chars):
        curr_deg = start_angle_deg + (i * angle_step if not flip else -i * angle_step)
        theta = math.radians(curr_deg)
        x = cx + radius * math.cos(theta)
        y = cy + radius * math.sin(theta)
        
        # Render single char onto high-res sub-image, rotate, and paste
        char_box_size = int(radius * 0.8)
        c_img = Image.new("RGBA", (char_box_size, char_box_size), (0, 0, 0, 0))
        c_draw = ImageDraw.Draw(c_img)
        c_draw.text((char_box_size // 2, char_box_size // 2), ch, font=font, fill=fill_color, anchor="mm")
        
        # Character rotation angle (tangent to circle)
        char_rot = curr_deg + 90.0 if not flip else curr_deg - 90.0
        rotated_c = c_img.rotate(-char_rot, resample=Image.BICUBIC)
        
        paste_x = int(x - char_box_size // 2)
        paste_y = int(y - char_box_size // 2)
        img.alpha_composite(rotated_c, (paste_x, paste_y))

def render_trust_seal_frame(
    progress: float,
    w: int,
    h: int,
    text_main: str,
    text_sub: str,
    text_arc: str,
    theme_name: str,
    position: str,
    custom_x: Optional[int],
    custom_y: Optional[int],
    animate_mode: str,
    size_px: int = 340
) -> Image.Image:
    """Renders a single frame of the trust seal with animation."""
    frame_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    
    # Scale animation: Spring bounce entry (0 -> 0.18s), hold, smooth exit (0.88 -> 1.0)
    if progress < 0.15:
        t = progress / 0.15
        scale = ease_out_back(t)
    elif progress > 0.88:
        t = (1.0 - progress) / 0.12
        scale = max(0.0, t)
    else:
        if animate_mode == "pulse":
            scale = 1.0 + 0.04 * math.sin((progress - 0.15) * math.pi * 8)
        else:
            scale = 1.0
            
    if scale <= 0.05:
        return frame_img
        
    seal_size = int(size_px * scale)
    half_size = seal_size // 2
    
    # Determine position
    if custom_x is not None and custom_y is not None:
        cx, cy = custom_x, custom_y
    elif position == "bottom_right":
        cx = int(w * 0.80)
        cy = int(h * 0.82)
    elif position == "bottom_left":
        cx = int(w * 0.20)
        cy = int(h * 0.82)
    elif position == "top_right":
        cx = int(w * 0.80)
        cy = int(h * 0.18)
    elif position == "top_left":
        cx = int(w * 0.20)
        cy = int(h * 0.18)
    else:  # center
        cx = w // 2
        cy = h // 2
        
    theme = SEAL_THEMES.get(theme_name.lower(), SEAL_THEMES["gold_luxury"])
    
    # Render seal onto its own canvas
    seal_canvas = Image.new("RGBA", (seal_size * 2, seal_size * 2), (0, 0, 0, 0))
    sc_cx = seal_size
    sc_cy = seal_size
    draw = ImageDraw.Draw(seal_canvas)
    
    # Rotation angle
    rot_deg = (progress * 72.0) if animate_mode == "rotate" else 0.0
    
    # 1. Ribbon tails (underneath)
    ribbon_w = int(seal_size * 0.26)
    ribbon_h = int(seal_size * 0.55)
    r_color = theme["ribbon"]
    
    # Left tail
    l_pts = [
        (sc_cx - int(seal_size * 0.25), sc_cy + int(seal_size * 0.25)),
        (sc_cx - int(seal_size * 0.38), sc_cy + ribbon_h),
        (sc_cx - int(seal_size * 0.25), sc_cy + ribbon_h - int(seal_size * 0.08)),
        (sc_cx - int(seal_size * 0.12), sc_cy + ribbon_h),
        (sc_cx - int(seal_size * 0.05), sc_cy + int(seal_size * 0.35))
    ]
    draw.polygon(l_pts, fill=r_color, outline=theme["secondary"], width=2)
    
    # Right tail
    r_pts = [
        (sc_cx + int(seal_size * 0.25), sc_cy + int(seal_size * 0.25)),
        (sc_cx + int(seal_size * 0.38), sc_cy + ribbon_h),
        (sc_cx + int(seal_size * 0.25), sc_cy + ribbon_h - int(seal_size * 0.08)),
        (sc_cx + int(seal_size * 0.12), sc_cy + ribbon_h),
        (sc_cx + int(seal_size * 0.05), sc_cy + int(seal_size * 0.35))
    ]
    draw.polygon(r_pts, fill=r_color, outline=theme["secondary"], width=2)
    
    # 2. Outer Scalloped Rosette Edge
    rosette_r = int(half_size * 0.95)
    rosette_pts = render_scalloped_rosette(
        radius=rosette_r,
        num_teeth=28,
        tooth_depth=int(seal_size * 0.04),
        rotation_deg=rot_deg
    )
    shifted_rosette = [(px + sc_cx, py + sc_cy) for px, py in rosette_pts]
    # Drop shadow
    shadow_rosette = [(px + sc_cx + 4, py + sc_cy + 4) for px, py in rosette_pts]
    draw.polygon(shadow_rosette, fill=(0, 0, 0, 160))
    # Outer gold teeth
    draw.polygon(shifted_rosette, fill=theme["secondary"], outline=theme["primary"], width=3)
    
    # 3. Inner Concentric Rings
    ring1_r = int(half_size * 0.84)
    draw.ellipse(
        [sc_cx - ring1_r, sc_cy - ring1_r, sc_cx + ring1_r, sc_cy + ring1_r],
        fill=theme["primary"],
        outline=theme["secondary"],
        width=2
    )
    
    # Dark Medallion Core
    core_r = int(half_size * 0.76)
    draw.ellipse(
        [sc_cx - core_r, sc_cy - core_r, sc_cx + core_r, sc_cy + core_r],
        fill=theme["core_bg"],
        outline=theme["primary"],
        width=3
    )
    
    # Inner Dotted/Accent Ring
    accent_r = int(half_size * 0.70)
    draw.ellipse(
        [sc_cx - accent_r, sc_cy - accent_r, sc_cx + accent_r, sc_cy + accent_r],
        outline=(theme["primary"][0], theme["primary"][1], theme["primary"][2], 140),
        width=1
    )
    
    # 4. Circular Arc Text along top
    arc_text = text_arc.upper() if text_arc else "MONEY BACK GUARANTEE"
    arc_font_size = max(10, int(seal_size * 0.055))
    arc_font = get_best_font(arc_font_size, bold=True)
    draw_circular_text(
        img=seal_canvas,
        text=arc_text,
        cx=sc_cx,
        cy=sc_cy,
        radius=core_r * 0.74,
        start_angle_deg=-140.0,
        span_deg=100.0,
        font=arc_font,
        fill_color=theme["primary"],
        flip=False
    )
    
    # 5. Center 5 Stars
    star_y = sc_cy - int(seal_size * 0.08)
    star_spacing = int(seal_size * 0.08)
    for s_idx in range(5):
        sx = sc_cx + (s_idx - 2) * star_spacing
        draw_star(
            draw=draw,
            cx=sx,
            cy=star_y,
            r_out=int(seal_size * 0.038),
            r_in=int(seal_size * 0.018),
            fill_color=theme["primary"]
        )
        
    # 6. Main Bold Center Text (e.g. '90 DAYS' or '100%')
    main_font_size = max(14, int(seal_size * 0.16))
    main_font = get_best_font(main_font_size, bold=True)
    draw.text(
        (sc_cx, sc_cy + int(seal_size * 0.04)),
        text_main.upper(),
        font=main_font,
        fill=theme["text"],
        anchor="mm"
    )
    
    # 7. Center Subtext (e.g. 'RISK FREE' or 'CERTIFIED')
    if text_sub:
        sub_font_size = max(9, int(seal_size * 0.065))
        sub_font = get_best_font(sub_font_size, bold=True)
        draw.text(
            (sc_cx, sc_cy + int(seal_size * 0.18)),
            text_sub.upper(),
            font=sub_font,
            fill=theme["primary"],
            anchor="mm"
        )
        
    # 8. Specular Light Sheen Animation (Diagonal light sweep across badge)
    if animate_mode in {"sheen", "default"}:
        sheen_cycle = (progress * 3.5) % 1.0  # sweeps every ~1s
        if sheen_cycle < 0.35:
            sheen_p = sheen_cycle / 0.35
            sheen_canvas = Image.new("RGBA", seal_canvas.size, (0, 0, 0, 0))
            s_draw = ImageDraw.Draw(sheen_canvas)
            
            # Diagonal beam coordinates
            beam_offset = int((sheen_p - 0.5) * seal_size * 3.0)
            p1 = (sc_cx + beam_offset - int(seal_size * 0.4), sc_cy - seal_size)
            p2 = (sc_cx + beam_offset - int(seal_size * 0.1), sc_cy - seal_size)
            p3 = (sc_cx + beam_offset + int(seal_size * 0.4), sc_cy + seal_size)
            p4 = (sc_cx + beam_offset + int(seal_size * 0.1), sc_cy + seal_size)
            
            s_draw.polygon([p1, p2, p3, p4], fill=(255, 255, 255, 75))
            # Mask sheen within the circular core
            mask_img = Image.new("L", seal_canvas.size, 0)
            m_draw = ImageDraw.Draw(mask_img)
            m_draw.ellipse([sc_cx - core_r, sc_cy - core_r, sc_cx + core_r, sc_cy + core_r], fill=255)
            
            seal_canvas.paste(sheen_canvas, (0, 0), mask=mask_img)
            
    # Paste centered onto main video frame
    paste_x = int(cx - sc_cx)
    paste_y = int(cy - sc_cy)
    frame_img.alpha_composite(seal_canvas, (paste_x, paste_y))
    return frame_img

@app.command()
def apply(
    input_file: Path = typer.Option(..., "--input", "-i", help="Input video file path"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Output video file path"),
    main_text: str = typer.Option("90 DAYS", "--text", "-t", help="Primary center badge text (e.g. '90 DAYS', '100%', 'DERM')"),
    sub_text: str = typer.Option("RISK FREE", "--subtext", help="Secondary center subtext (e.g. 'RISK FREE', 'APPROVED')"),
    arc_text: str = typer.Option("MONEY BACK GUARANTEE", "--arc-text", help="Circular arc text (e.g. 'MONEY BACK GUARANTEE', 'CLINICALLY PROVEN')"),
    theme: str = typer.Option("gold_luxury", "--theme", help="Seal theme: 'gold_luxury', 'medical_clean', 'emerald_trust', 'crimson_seal'"),
    position: str = typer.Option("bottom_right", "--pos", help="Placement preset: 'bottom_right', 'bottom_left', 'top_right', 'top_left', 'center'"),
    custom_x: Optional[int] = typer.Option(None, "--x", help="Exact custom center X coordinate"),
    custom_y: Optional[int] = typer.Option(None, "--y", help="Exact custom center Y coordinate"),
    size: int = typer.Option(340, "--size", help="Trust seal diameter in pixels (default: 340)"),
    animate: str = typer.Option("sheen", "--animate", "-a", help="Animation style: 'sheen' (periodic specular light sweep), 'rotate', 'pulse', 'static'"),
    start_time: float = typer.Option(0.0, "--start", "-s", help="Start timestamp in seconds"),
    duration: Optional[float] = typer.Option(None, "--duration", "-d", help="Display duration in seconds (defaults to rest of video)"),
    sfx: bool = typer.Option(True, "--sfx/--no-sfx", help="Mix synchronized reveal chime sound effect")
):
    """
    Renders animated trust seals, guarantee rosettes, and risk-reversal badges.
    """
    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file '{input_file}' not found![/bold red]")
        raise typer.Exit(1)
        
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_file is None:
        output_file = output_dir / f"{input_file.stem}_trust_seal.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    console.print(f"[bold cyan]Analyzing input video specs:[/bold cyan] {input_file.name}")
    w, h, fps, total_dur = get_video_specs(input_file, ffprobe_exe)
    console.print(f"  • Resolution: {w}x{h} @ {fps:.2f} fps | Duration: {total_dur:.2f}s")
    
    if duration is None:
        eff_dur = max(0.5, total_dur - start_time)
    else:
        eff_dur = min(duration, total_dur - start_time)
        
    end_time = start_time + eff_dur
    total_seal_frames = max(1, int(eff_dur * fps))
    console.print(f"[cyan]Rendering {total_seal_frames} trust seal overlay frames ({eff_dur:.2f}s duration)...[/cyan]")
    
    overlay_clip = output_dir / f"temp_seal_{input_file.stem}.mov"
    
    pipe_cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "rgba",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "qtrle",
        "-r", str(fps),
        str(overlay_clip)
    ]
    
    proc = subprocess.Popen(pipe_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    for f_idx in range(total_seal_frames):
        p = f_idx / float(total_seal_frames)
        frame_img = render_trust_seal_frame(
            progress=p,
            w=w,
            h=h,
            text_main=main_text,
            text_sub=sub_text,
            text_arc=arc_text,
            theme_name=theme,
            position=position,
            custom_x=custom_x,
            custom_y=custom_y,
            animate_mode=animate,
            size_px=size
        )
        proc.stdin.write(frame_img.tobytes())
        
    proc.stdin.close()
    proc.wait()
    console.print("[green]Transparent trust seal sequence generated.[/green]")
    
    # SFX selection
    sfx_path = None
    if sfx:
        for cand in ["SFX/UI Beep 5.wav", "SFX/Scene Change .mp3", "SFX/Switch Click.mp3", "SFX/whoosh-6316.mp3"]:
            if os.path.exists(cand):
                sfx_path = cand
                break
                
    console.print(f"[cyan]Compositing trust seal overlay into video stream...[/cyan]")
    if sfx_path:
        console.print(f"[cyan]Mixing synchronized SFX: [bold]{sfx_path}[/bold] at {start_time:.2f}s...[/cyan]")
        delay_ms = int(start_time * 1000)
        filter_complex = (
            f"[0:v][1:v]overlay=0:0:enable='between(t,{start_time:.3f},{end_time:.3f})'[outv];"
            f"[2:a]adelay={delay_ms}|{delay_ms},volume=0.35[sfx_delayed];"
            f"[0:a][sfx_delayed]amix=inputs=2:duration=first:dropout_transition=2[outa]"
        )
        composite_cmd = [
            ffmpeg_exe,
            "-y",
            "-i", str(input_file),
            "-itsoffset", f"{start_time:.3f}",
            "-i", str(overlay_clip),
            "-i", str(sfx_path),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_file)
        ]
    else:
        composite_cmd = [
            ffmpeg_exe,
            "-y",
            "-i", str(input_file),
            "-itsoffset", f"{start_time:.3f}",
            "-i", str(overlay_clip),
            "-filter_complex", f"[0:v][1:v]overlay=0:0:enable='between(t,{start_time:.3f},{end_time:.3f})'[outv]",
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "copy",
            str(output_file)
        ]
        
    subprocess.run(composite_cmd, check=True)
    
    if overlay_clip.exists():
        overlay_clip.unlink()
        
    console.print(f"\n[bold green]Success![/bold green] Trust seal applied! Video saved to: [bold]{output_file}[/bold]")

if __name__ == "__main__":
    app()
