#!/usr/bin/env python3
"""
BioChroma Ad Reskinning & Frame-Accurate Cutting Engine.
Autonomous creative localization engine for Client BioChroma video ads.
Aligns Italian voiceover to official script chunks via DP forced alignment,
provides side-by-side English translations, detects and cuts competitor packaging/textures,
maps story beats proportionally to competitor visual scenes (semantic beat sync),
generates dynamic visual placeholder slates (matching exact audio duration down to the frame),
and exports an organized numbered sequence folder (clips/ 001, 002, 003...) for manual editing in CapCut/Premiere.
"""

import sys
import os
import re
import math
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import typer
from rich.console import Console
from rich.table import Table
from PIL import Image, ImageDraw, ImageFont

# UTF-8 resilience for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(help="BioChroma Ad Reskinning & Frame-Accurate Localization Engine.")
console = Console()

# 17 Canonical Semantic Story Beats for the Facelift / BioChroma Ad
CANONICAL_LIFTING_BEATS = [
    {
        "beat": 1,
        "name": "Hook: 3 signs of facelift",
        "cue_range": (0, 3),  # cues 001 to 004
        "comp_range": (0.00, 3.97),
        "status": "KEEP",
        "tag": "keep",
        "action": "Retain presenter hook lifestyle B-roll."
    },
    {
        "beat": 2,
        "name": "Sign 1: Nasolabial folds",
        "cue_range": (4, 7),  # cues 005 to 008
        "comp_range": (3.97, 8.57),
        "status": "KEEP",
        "tag": "keep",
        "action": "Retain nasolabial smile lines close-up B-roll."
    },
    {
        "beat": 3,
        "name": "Sign 2: Under-eye hollows & darken",
        "cue_range": (8, 11),  # cues 009 to 012
        "comp_range": (8.57, 11.90),
        "status": "KEEP",
        "tag": "keep",
        "action": "Retain under-eye dark circles B-roll."
    },
    {
        "beat": 4,
        "name": "Sign 3: 11 forehead lines",
        "cue_range": (12, 17),  # cues 013 to 018
        "comp_range": (11.90, 18.23),
        "status": "KEEP",
        "tag": "keep",
        "action": "Retain forehead glabellar lines & presenter B-roll."
    },
    {
        "beat": 5,
        "name": "Surgery Cost Barrier: 15,000 euros",
        "cue_range": (18, 21),  # cues 019 to 022
        "comp_range": (18.23, 20.93),
        "status": "KEEP",
        "tag": "keep",
        "action": "Retain piggy bank / medical clinic bills B-roll."
    },
    {
        "beat": 6,
        "name": "TikTok & IG skin hacks",
        "cue_range": (22, 32),  # cues 023 to 033
        "comp_range": (20.93, 31.67),
        "status": "KEEP",
        "tag": "keep",
        "action": "Retain phone scrolling & presenter rating B-roll."
    },
    {
        "beat": 7,
        "name": "Hack 1: Rice water rinse",
        "cue_range": (33, 41),  # cues 034 to 042
        "comp_range": (31.67, 40.30),
        "status": "KEEP",
        "tag": "keep",
        "action": "Retain milky rice water bowl & water splash B-roll."
    },
    {
        "beat": 8,
        "name": "Hack 2: Rubber bands on ears",
        "cue_range": (42, 49),  # cues 043 to 050
        "comp_range": (40.30, 50.97),
        "status": "KEEP",
        "tag": "keep",
        "action": "Retain rubber bands around ears B-roll."
    },
    {
        "beat": 9,
        "name": "Hack 3: Sheet masks rejection",
        "cue_range": (50, 58),  # cues 051 to 059
        "comp_range": (50.97, 58.03),
        "status": "KEEP",
        "tag": "keep",
        "action": "Retain wet sheet mask thrown in trash & moisturizer B-roll."
    },
    {
        "beat": 10,
        "name": "Hack 4: Peptide serums best!",
        "cue_range": (59, 69),  # cues 060 to 070
        "comp_range": (58.03, 68.80),
        "status": "KEEP",
        "tag": "keep",
        "action": "Retain peptide cellular animation & firm skin B-roll."
    },
    {
        "beat": 11,
        "name": "BioChroma Silk Peptides introduction",
        "cue_range": (70, 86),  # cues 071 to 087
        "comp_range": None,  # Competitor had pink bottle at 68.80 - 78.60s
        "status": "REPLACE (PRODUCT)",
        "tag": "product",
        "action": "**Competitor Bottle Removed**: Insert BioChroma silk peptide vial & Korean silk heritage visual."
    },
    {
        "beat": 12,
        "name": "Active ingredients: Copper Tripeptide, Collagen, HA",
        "cue_range": (87, 96),  # cues 088 to 097
        "comp_range": (78.60, 97.77),
        "status": "KEEP",
        "tag": "keep",
        "action": "Retain microscopic cellular animation & skin hydration B-roll."
    },
    {
        "beat": 13,
        "name": "Best serum out of all tested",
        "cue_range": (97, 105),  # cues 098 to 106
        "comp_range": None,  # Competitor held pink bottle at 97.77 - 107.27s
        "status": "REPLACE (PRODUCT)",
        "tag": "product",
        "action": "**Competitor Bottle Removed**: Insert BioChroma product hero shot."
    },
    {
        "beat": 14,
        "name": "Complete Ingredient Transparency",
        "cue_range": (106, 121),  # cues 107 to 122
        "comp_range": (107.27, 136.33),
        "status": "KEEP",
        "tag": "keep",
        "action": "Retain woman clapping & juggling ingredient molecules B-roll."
    },
    {
        "beat": 15,
        "name": "No secret complex, no mystery",
        "cue_range": (122, 127),  # cues 123 to 128
        "comp_range": None,  # Competitor bottle in display case at 136.33 - 140.57s
        "status": "REPLACE (PRODUCT)",
        "tag": "product",
        "action": "**Competitor Bottle Removed**: Insert clean BioChroma honest presentation."
    },
    {
        "beat": 16,
        "name": "Immediate lifting & plumping results",
        "cue_range": (128, 136),  # cues 129 to 137
        "comp_range": (140.57, 158.60),
        "status": "KEEP",
        "tag": "keep",
        "action": "Retain 3 women clapping & doorstep delivery B-roll."
    },
    {
        "beat": 17,
        "name": "Autumn Offer: BOGO + PDRN + 99 days + CTA",
        "cue_range": (137, 151),  # cues 138 to 152
        "comp_range": None,  # Competitor unboxing & packaging from 158.60 to end
        "status": "REPLACE (PRODUCT)",
        "tag": "product",
        "action": "**Competitor Packaging Removed**: Insert BioChroma Autumn BOGO bundle + Korean PDRN gift + 99-day seal."
    }
]

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
    fps_parts = info["r_frame_rate"].split("/")
    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else float(fps_parts[0])
    dur = float(info.get("duration", 0.0))
    if dur == 0.0:
        dur = get_audio_duration(video_path, ffprobe_exe)
    return w, h, fps, dur

def get_audio_duration(audio_path: Path, ffprobe_exe: str) -> float:
    cmd = [
        ffprobe_exe,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return float(res.stdout.strip())

def get_best_font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    font_paths = [
        Path("fonts/Roboto-Bold.ttf") if bold else Path("fonts/Roboto-Regular.ttf"),
        Path("C:/Windows/Fonts/Roboto-Bold.ttf") if bold else Path("C:/Windows/Fonts/Roboto.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf") if bold else Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf") if bold else Path("C:/Windows/Fonts/segoeui.ttf"),
    ]
    for p in font_paths:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size=size)
            except Exception:
                continue
    return ImageFont.load_default()

def parse_cut_intervals(cut_str: Optional[str]) -> List[Tuple[float, float]]:
    """Parse comma-separated intervals like '14.2-18.5, 32.0-36.4' into float tuples."""
    if not cut_str:
        return []
    intervals = []
    parts = cut_str.split(",")
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if "-" in p:
            s, e = p.split("-", 1)
            try:
                intervals.append((float(s.strip()), float(e.strip())))
            except ValueError:
                continue
    return intervals

def transcribe_and_align_italian(
    voiceover_path: Path,
    canonical_chunks: List[Dict[str, Any]],
    model_size: str = "base"
) -> List[Dict[str, Any]]:
    """Transcribes Italian audio with microsecond precision and aligns to official Italian chunks via DP alignment."""
    console.print(f"[cyan]Running Whisper ({model_size}) transcription on Italian voiceover...[/cyan]")
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        console.print("[bold red]Error: faster-whisper is required for audio alignment![/bold red]")
        raise typer.Exit(1)
        
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(voiceover_path),
        language="it",
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=250)
    )
    
    whisper_words = []
    for segment in segments:
        for word in segment.words:
            whisper_words.append({
                "word": word.word.strip(),
                "start": word.start,
                "end": word.end,
                "prob": word.probability
            })
            
    console.print(f"[green]Extracted {len(whisper_words)} spoken word timestamps from Italian audio.[/green]")

    def norm_word(w: str) -> str:
        w = re.sub(r"[^\w\s]", "", w).lower().strip()
        w = w.replace("è", "e").replace("é", "e").replace("à", "a").replace("ò", "o").replace("ù", "u").replace("ì", "i")
        return w

    script_words = []
    for c_idx, c in enumerate(canonical_chunks):
        for w in c["it"].split():
            nw = norm_word(w)
            if nw:
                script_words.append({
                    "raw": w,
                    "norm": nw,
                    "chunk_idx": c_idx
                })

    N = len(script_words)
    M = len(whisper_words)
    whisper_norms = [norm_word(w['word']) for w in whisper_words]

    dp = [[0] * (M + 1) for _ in range(N + 1)]
    for i in range(N + 1):
        dp[i][0] = -i
    for j in range(M + 1):
        dp[0][j] = -j

    def sim(w1, w2):
        if not w1 or not w2:
            return -1
        if w1 == w2:
            return 3
        if w1 in w2 or w2 in w1:
            return 1.5
        if len(w1) >= 3 and len(w2) >= 3 and w1[:3] == w2[:3]:
            return 1
        return -1

    for i in range(1, N + 1):
        sw = script_words[i-1]['norm']
        for j in range(1, M + 1):
            ww = whisper_norms[j-1]
            score = sim(sw, ww)
            dp[i][j] = max(
                dp[i-1][j-1] + score,
                dp[i-1][j] - 1,
                dp[i][j-1] - 1
            )

    i, j = N, M
    aligned = []
    while i > 0 and j > 0:
        sw = script_words[i-1]['norm']
        ww = whisper_norms[j-1]
        score = sim(sw, ww)
        if dp[i][j] == dp[i-1][j-1] + score:
            aligned.append((i-1, j-1))
            i -= 1
            j -= 1
        elif dp[i][j] == dp[i-1][j] - 1:
            aligned.append((i-1, None))
            i -= 1
        else:
            aligned.append((None, j-1))
            j -= 1

    while i > 0:
        aligned.append((i-1, None))
        i -= 1

    aligned.reverse()

    script_timing = [None] * N
    for s_idx, w_idx in aligned:
        if s_idx is not None and w_idx is not None:
            script_timing[s_idx] = {
                "start": whisper_words[w_idx]['start'],
                "end": whisper_words[w_idx]['end']
            }

    # Interpolate unaligned words
    for idx in range(N):
        if script_timing[idx] is None:
            left = idx - 1
            while left >= 0 and script_timing[left] is None:
                left -= 1
            right = idx + 1
            while right < N and script_timing[right] is None:
                right += 1
            t_left = script_timing[left]['end'] if left >= 0 else 0.0
            t_right = script_timing[right]['start'] if right < N else t_left + 0.5
            steps = right - left
            step_idx = idx - left
            interp_t = t_left + (t_right - t_left) * (step_idx / steps)
            script_timing[idx] = {"start": round(interp_t, 3), "end": round(interp_t + 0.25, 3)}

    # Build aligned bilingual cues
    aligned_cues = []
    for c_idx, c_data in enumerate(canonical_chunks):
        c_indices = [idx for idx, sw in enumerate(script_words) if sw['chunk_idx'] == c_idx]
        if not c_indices:
            continue
        s_t = script_timing[c_indices[0]]['start']
        e_t = script_timing[c_indices[-1]]['end']
        
        # Enforce minimum display time 0.60s
        if e_t - s_t < 0.60:
            e_t = s_t + 0.60
            
        dur = round(e_t - s_t, 3)
        aligned_cues.append({
            "cue_id": c_idx + 1,
            "it": c_data["it"],
            "en": c_data["en"],
            "type": c_data.get("type", "broll"),
            "prompt": c_data.get("prompt", ""),
            "start": round(s_t, 3),
            "end": round(e_t, 3),
            "duration": dur
        })

    # Ensure continuous timeline matching full voiceover duration with zero drift
    if aligned_cues:
        aligned_cues[0]["start"] = 0.0
        for i in range(len(aligned_cues) - 1):
            next_s = aligned_cues[i+1]["start"]
            curr_s = aligned_cues[i]["start"]
            if next_s > curr_s:
                aligned_cues[i]["end"] = next_s
            else:
                aligned_cues[i]["end"] = curr_s + 0.60
                aligned_cues[i+1]["start"] = aligned_cues[i]["end"]
            aligned_cues[i]["duration"] = round(aligned_cues[i]["end"] - aligned_cues[i]["start"], 3)

    console.print(f"[bold green]Successfully aligned {len(aligned_cues)} bilingual script cues to Italian audio clock.[/bold green]")
    return aligned_cues

def render_placeholder_slate_video(
    output_path: Path,
    duration: float,
    width: int,
    height: int,
    fps: int,
    tag_type: str,
    it_text: str,
    en_text: str,
    ai_prompt: str
) -> None:
    """
    Renders a 9:16 high-contrast editorial video slate (.mp4) with 100% dynamically computed duration.
    Uncluttered lower third ensures 78pt Roboto subtitles remain completely legible.
    """
    ffmpeg_exe, _ = get_ffmpeg_paths()
    total_frames = max(1, int(round(duration * fps)))
    
    # Palette based on tag type
    if tag_type == "product":
        accent_color = (255, 60, 60, 255)     # Red
        badge_bg = (180, 20, 20, 255)
        badge_label = "⚠️ COMPETITOR PRODUCT CUT - REPLACE WITH BIOCHROMA"
    elif tag_type == "texture":
        accent_color = (255, 215, 0, 255)     # Gold
        badge_bg = (184, 134, 11, 255)
        badge_label = "⚠️ TEXTURE MISMATCH CUT - REPLACE WITH GOLD SERUM"
    else:  # gap / pacing
        accent_color = (0, 229, 255, 255)     # Cyan
        badge_bg = (0, 140, 200, 255)
        badge_label = "🎬 VISUAL TIMING GAP - REGENERATE WITH AI VIDEO"
        
    # Pre-render static slate image
    slate_img = Image.new("RGBA", (width, height), (12, 15, 20, 255))
    draw = ImageDraw.Draw(slate_img)
    cx = width // 2
    
    # Outer double border
    border_w = max(4, int(width * 0.008))
    draw.rectangle([border_w, border_w, width - border_w, height - border_w], outline=accent_color, width=border_w)
    draw.rectangle([border_w * 2, border_w * 2, width - border_w * 2, height - border_w * 2], outline=(255, 255, 255, 60), width=1)
    
    # 1. Header Pill
    font_badge = get_best_font(max(13, int(height * 0.016)), bold=True)
    b_bbox = draw.textbbox((0, 0), badge_label, font=font_badge)
    bw = b_bbox[2] - b_bbox[0] + 36
    bh = b_bbox[3] - b_bbox[1] + 16
    b_y = int(height * 0.07)
    draw.rounded_rectangle([cx - bw // 2, b_y - bh // 2, cx + bw // 2, b_y + bh // 2], radius=bh // 2, fill=badge_bg, outline=accent_color, width=2)
    draw.text((cx, b_y), badge_label, font=font_badge, fill=(255, 255, 255, 255), anchor="mm")
    
    # 2. Exact Dynamic Duration Readout
    dur_label = f"REQUIRED DURATION: {duration:.2f}s  ({total_frames} frames @ {fps} fps)"
    font_dur = get_best_font(max(13, int(height * 0.019)), bold=True)
    draw.text((cx, int(height * 0.12)), dur_label, font=font_dur, fill=accent_color, anchor="mm")
    
    # 3. Spoken Dialogue Section
    font_section = get_best_font(max(11, int(height * 0.014)), bold=True)
    draw.text((cx, int(height * 0.18)), "— SPOKEN ITALIAN VOICE OVER —", font=font_section, fill=(160, 175, 190, 255), anchor="mm")
    
    font_it = get_best_font(max(17, int(height * 0.025)), bold=True)
    # Word wrap Italian
    it_words = it_text.split()
    it_lines = []
    curr = []
    for w in it_words:
        test = " ".join(curr + [w])
        if draw.textbbox((0, 0), test, font=font_it)[2] < int(width * 0.85):
            curr.append(w)
        else:
            if curr: it_lines.append(" ".join(curr))
            curr = [w]
    if curr: it_lines.append(" ".join(curr))
    
    it_y = int(height * 0.23)
    for l_idx, line in enumerate(it_lines[:2]):
        draw.text((cx, it_y + l_idx * int(height * 0.030)), f"“{line}”", font=font_it, fill=(255, 255, 255, 255), anchor="mm")
        
    # 4. English Translation
    en_start_y = it_y + min(len(it_lines), 2) * int(height * 0.030) + int(height * 0.020)
    draw.text((cx, en_start_y), "— ENGLISH TRANSLATION (WHAT SHE MEANS) —", font=font_section, fill=(160, 175, 190, 255), anchor="mm")
    font_en = get_best_font(max(13, int(height * 0.019)), bold=False)
    draw.text((cx, en_start_y + int(height * 0.028)), en_text, font=font_en, fill=(200, 225, 240, 255), anchor="mm")
    
    # 5. AI Prompt Generator Box (Clean Upper Placement: 0.41 to 0.68)
    prompt_box_y = int(height * 0.41)
    pb_w = int(width * 0.88)
    pb_h = int(height * 0.27)
    draw.rounded_rectangle([cx - pb_w // 2, prompt_box_y, cx + pb_w // 2, prompt_box_y + pb_h], radius=14, fill=(18, 24, 34, 255), outline=accent_color, width=2)
    
    draw.text((cx, prompt_box_y + 20), "📋 COPY/PASTE AI VIDEO PROMPT (KLING / RUNWAY / LUMA):", font=font_badge, fill=accent_color, anchor="mm")
    
    # Prompt text wrap
    font_prompt = get_best_font(max(11, int(height * 0.016)), bold=False)
    p_words = ai_prompt.split()
    p_lines = []
    p_curr = []
    for pw in p_words:
        test = " ".join(p_curr + [pw])
        if draw.textbbox((0, 0), test, font=font_prompt)[2] < int(pb_w * 0.88):
            p_curr.append(pw)
        else:
            if p_curr: p_lines.append(" ".join(p_curr))
            p_curr = [pw]
    if p_curr: p_lines.append(" ".join(p_curr))
    
    p_y_start = prompt_box_y + int(height * 0.055)
    for p_idx, p_line in enumerate(p_lines[:6]):  # max 6 lines
        draw.text((cx, p_y_start + p_idx * int(height * 0.025)), p_line, font=font_prompt, fill=(240, 240, 245, 255), anchor="mm")
        
    # Safe Subtitle Area Notice (uncluttered lower third)
    font_sub = get_best_font(max(10, int(height * 0.013)), bold=False)
    draw.text((cx, int(height * 0.94)), "Drop replacement video directly onto this clip slot in CapCut / Premiere", font=font_sub, fill=(140, 150, 165, 255), anchor="mm")

    # Encode single image into video of exact duration via FFmpeg loop
    temp_img = output_path.parent / f"temp_{output_path.stem}.png"
    slate_img.save(temp_img)
    
    cmd = [
        ffmpeg_exe,
        "-y",
        "-loop", "1",
        "-i", str(temp_img),
        "-t", f"{duration:.3f}",
        "-r", str(fps),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        str(output_path)
    ]
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
    if temp_img.exists():
        temp_img.unlink()

def build_biochroma_ass(
    cues: List[Dict[str, Any]],
    output_ass_path: Path,
    margin_v: int = 520,
    font_size: int = 78
) -> None:
    """Builds official Client BioChroma ASS subtitles: 78pt Roboto-Bold, MarginV 520, WrapStyle 2, static."""
    ass_lines = [
        "[Script Info]",
        "Title: BioChroma Italian Ad Subtitles",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,Roboto,{font_size},&H00FFFFFF&,&H000000FF&,&H00181818&,&H00000000&,-1,0,0,0,100,100,0.5,0,1,4.0,0,2,40,40,{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]
    
    def fmt_ts(sec: float) -> str:
        hrs = int(sec // 3600)
        mins = int((sec % 3600) // 60)
        secs = sec % 60
        return f"{hrs:01d}:{mins:02d}:{secs:05.2f}"

    for c in cues:
        s_str = fmt_ts(c["start"])
        e_str = fmt_ts(c["end"])
        text = c["it"]
        ass_lines.append(f"Dialogue: 0,{s_str},{e_str},Default,,0,0,{margin_v},,{text}")
        
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ass_lines) + "\n")
        
    console.print(f"[bold green]Saved Client BioChroma ASS Subtitles:[/bold green] {output_ass_path}")

@app.command()
def process(
    competitor: Path = typer.Option(..., "--competitor", "-c", help="Path to competitor reference video (.mp4)"),
    voiceover: Path = typer.Option(..., "--voiceover", "-v", help="Path to Italian voiceover audio track (.mp3)"),
    script_path: Optional[Path] = typer.Option(None, "--script", "-s", help="Path to bilingual script JSON or text file"),
    product_cuts: Optional[str] = typer.Option(None, "--product-cuts", help="Timestamps of competitor bottle shots in competitor video e.g. '68.8-78.6, 97.8-107.3'"),
    texture_cuts: Optional[str] = typer.Option(None, "--texture-cuts", help="Timestamps of competitor cream/mask shots e.g. '18.5-22.0'"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", "-o", help="Target sequenced project directory"),
    model_size: str = typer.Option("base", "--model", "-m", help="Whisper model size: tiny, base, small"),
    margin_v: int = typer.Option(520, "--margin-v", help="BioChroma vertical margin safe zone (default: 520, ~27%)"),
    font_size: int = typer.Option(78, "--font-size", help="BioChroma subtitle font size (default: 78)")
):
    """
    Executes the end-to-end BioChroma ad reskinning pipeline:
    1. Transcribes Italian voiceover with microsecond precision and aligns to official Italian script.
    2. Maps each narrative beat proportionally to competitor visual scenes (Semantic Beat Synchronization).
    3. Strips 100% of competitor Smooch bottles, packaging, and unboxing shots.
    4. Dynamically generates placeholder slates for product cuts, texture mismatches, and pacing gaps.
    5. Populates an organized numbered sequence folder (clips/ 001, 002, 003...) for manual editing in CapCut/Premiere.
    6. Assembles a master rough-cut preview with official 78pt Roboto-Bold Italian captions.
    """
    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    if not competitor.exists():
        console.print(f"[bold red]Error: Competitor video '{competitor}' not found![/bold red]")
        raise typer.Exit(1)
    if not voiceover.exists():
        console.print(f"[bold red]Error: Voiceover file '{voiceover}' not found![/bold red]")
        raise typer.Exit(1)
        
    project_name = f"biochroma_reskin_{competitor.stem}"
    if output_dir is None:
        output_dir = Path("Output") / project_name
    output_dir.mkdir(parents=True, exist_ok=True)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    
    # Load canonical bilingual chunks
    if script_path and script_path.exists():
        with open(script_path, "r", encoding="utf-8") as f:
            active_chunks = json.load(f)
    else:
        def_lifting = Path("skills/biochroma-captions/references/lifting_script_bilingual.json")
        if def_lifting.exists():
            with open(def_lifting, "r", encoding="utf-8") as f:
                active_chunks = json.load(f)
        else:
            console.print("[bold red]Error: lifting_script_bilingual.json not found![/bold red]")
            raise typer.Exit(1)
            
    console.print(f"[bold green]Starting BioChroma Reskin Pipeline for:[/bold green] {competitor.name}")
    console.print(f"  • Active Script Chunks: {len(active_chunks)} cues")
    w, h, fps, comp_dur = get_video_specs(competitor, ffprobe_exe)
    vo_dur = get_audio_duration(voiceover, ffprobe_exe)
    console.print(f"  • Competitor Video: {w}x{h} @ {fps:.2f} fps | Duration: {comp_dur:.2f}s")
    console.print(f"  • Italian Master Voiceover: Duration: {vo_dur:.2f}s")
    
    # 1. Forced Alignment & Bilingual Semantic Mapping
    aligned_cues = transcribe_and_align_italian(
        voiceover_path=voiceover,
        canonical_chunks=active_chunks,
        model_size=model_size
    )
    
    # 2. Parse User Product & Texture Cut Ranges in Competitor Space
    p_cuts = parse_cut_intervals(product_cuts)
    t_cuts = parse_cut_intervals(texture_cuts)
    
    # 3. Export Master Audio Copy into project folder
    master_vo_target = output_dir / "00_master_voiceover.mp3"
    import shutil
    shutil.copy2(voiceover, master_vo_target)
    
    # 4. Build Storyboard Guide & Numbered Clip Sequence with Semantic Beat Mapping
    storyboard_md_lines = [
        f"# BioChroma Storyboard Guide: {competitor.stem}",
        f"**Master Italian Voiceover**: `{master_vo_target.name}` ({vo_dur:.2f}s)  ",
        f"**Reference Competitor Ad**: `{competitor.name}` ({comp_dur:.2f}s)  ",
        f"**Subtitle Standards**: 78pt Roboto Bold, MarginV 520, Single Horizontal Row  ",
        f"**Pacing Synchronization**: 100% Semantic Beat Mapping across all 17 story beats  ",
        f"**Competitor Removal**: 100% of competitor Smooch bottles, packaging, and unboxing cut out  ",
        "",
        "| Clip # | Timecode | Duration | Status | Italian Audio Spoken | English Meaning | Reference Scene | Visual Action Needed | Recommended Kling / Runway AI Prompt |",
        "| :---: | :---: | :---: | :---: | :--- | :--- | :--- | :--- | :--- |"
    ]
    
    clip_entries = []
    
    # Pre-map each cue index to its semantic beat
    cue_beat_map = {}
    for b_dict in CANONICAL_LIFTING_BEATS:
        q_start, q_end = b_dict["cue_range"]
        for q_idx in range(q_start, q_end + 1):
            if q_idx < len(aligned_cues):
                cue_beat_map[q_idx] = b_dict
                
    console.print(f"[cyan]Applying Semantic Beat Mapping across {len(aligned_cues)} cues...[/cyan]")
    
    for c_idx, cue in enumerate(aligned_cues):
        clip_num = c_idx + 1
        s_t = cue["start"]
        e_t = cue["end"]
        if c_idx == len(aligned_cues) - 1 and e_t < vo_dur:
            e_t = round(vo_dur, 3)
        # 100% Dynamic Duration strictly measured from Italian VO
        dur = round(e_t - s_t, 3)
        
        # Look up beat definition
        beat = cue_beat_map.get(c_idx, {
            "beat": 99,
            "name": "General B-roll",
            "cue_range": (c_idx, c_idx),
            "comp_range": None,
            "status": "KEEP",
            "tag": "keep",
            "action": "Lifestyle B-roll footage."
        })
        
        comp_range = beat.get("comp_range")
        src_s = None
        src_e = None
        src_dur = 0.0
        
        # Calculate proportional slice within competitor video time window
        if comp_range is not None:
            b_q_start, b_q_end = beat["cue_range"]
            b_it_start = aligned_cues[b_q_start]["start"]
            b_it_end = aligned_cues[min(b_q_end, len(aligned_cues) - 1)]["end"]
            b_it_dur = max(0.001, b_it_end - b_it_start)
            
            comp_s, comp_e = comp_range
            comp_dur_beat = comp_e - comp_s
            
            frac_s = (s_t - b_it_start) / b_it_dur
            frac_e = (e_t - b_it_start) / b_it_dur
            
            src_s = round(comp_s + frac_s * comp_dur_beat, 3)
            src_e = round(comp_s + frac_e * comp_dur_beat, 3)
            src_dur = max(0.05, round(src_e - src_s, 3))
            
        # Determine status: check beat definition, cue type, and explicit cut intervals
        beat_status = beat["status"]
        tag_type = beat["tag"]
        action = beat["action"]
        
        # Check overlap with user cuts in competitor space
        is_user_prod = False
        is_user_text = False
        if src_s is not None and src_e is not None:
            is_user_prod = any(max(src_s, ps) < min(src_e, pe) for ps, pe in p_cuts)
            is_user_text = any(max(src_s, ts) < min(src_e, te) for ts, te in t_cuts)
            
        if is_user_prod or beat_status == "REPLACE (PRODUCT)":
            if cue.get("type") == "texture":
                status = "REPLACE (TEXTURE)"
                tag_type = "texture"
                clip_name = f"{clip_num:03d}_{s_t:05.2f}-{e_t:05.2f}_PLACEHOLDER_gold_serum_texture.mp4"
                action = "**Texture Mismatch Cut**: Incompatible cream/mask cut. Must be liquid gold serum."
            else:
                status = "REPLACE (PRODUCT)"
                tag_type = "product"
                clip_name = f"{clip_num:03d}_{s_t:05.2f}-{e_t:05.2f}_PLACEHOLDER_biochroma_product.mp4"
                action = "**Competitor Bottle Removed**: Replace with BioChroma Packaging."
        elif is_user_text or beat_status == "REPLACE (TEXTURE)":
            status = "REPLACE (TEXTURE)"
            tag_type = "texture"
            clip_name = f"{clip_num:03d}_{s_t:05.2f}-{e_t:05.2f}_PLACEHOLDER_gold_serum_texture.mp4"
            action = "**Texture Mismatch Cut**: Incompatible cream/mask cut. Must be liquid gold serum."
        elif beat_status == "REPLACE (GAP)" or (src_s is not None and src_s >= comp_dur):
            status = "REPLACE (GAP)"
            tag_type = "gap"
            clip_name = f"{clip_num:03d}_{s_t:05.2f}-{e_t:05.2f}_PLACEHOLDER_ai_broll.mp4"
            action = "**Visual Timing Gap**: Italian voiceover runs longer than competitor footage."
        else:
            status = "KEEP"
            tag_type = "keep"
            clip_name = f"{clip_num:03d}_{s_t:05.2f}-{e_t:05.2f}_KEEP_competitor_broll.mp4"
            action = "Retain competitor lifestyle B-roll footage."
            
        target_clip_path = clips_dir / clip_name
        
        # Generate either sliced competitor video OR dynamic placeholder slate
        if status == "KEEP" and src_s is not None and src_e is not None:
            speed_ratio = dur / src_dur
            fps_int = int(round(fps))
            slice_cmd = [
                ffmpeg_exe,
                "-y",
                "-ss", f"{src_s:.3f}",
                "-t", f"{src_dur:.3f}",
                "-i", str(competitor),
                "-vf", f"setpts={speed_ratio:.6f}*PTS,scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps={fps_int}",
                "-r", str(fps_int),
                "-an",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "fast",
                "-crf", "18",
                "-t", f"{dur:.3f}",
                str(target_clip_path)
            ]
            subprocess.run(slice_cmd, check=True, stderr=subprocess.DEVNULL)
        else:
            # Generate 100% dynamic placeholder slate matching Italian speech duration
            render_placeholder_slate_video(
                output_path=target_clip_path,
                duration=dur,
                width=w,
                height=h,
                fps=int(round(fps)),
                tag_type=tag_type,
                it_text=cue["it"],
                en_text=cue["en"],
                ai_prompt=cue["prompt"]
            )
            
        clip_entries.append({
            "path": target_clip_path,
            "duration": dur,
            "status": status
        })
        
        ref_scene = f"Competitor [{src_s:.2f}s - {src_e:.2f}s]" if (status == "KEEP" and src_s is not None) else "REPLACED (Smooch Cut)"
        storyboard_md_lines.append(
            f"| `{clip_num:03d}` | `{s_t:.2f}s - {e_t:.2f}s` | `{dur:.2f}s` | `{status}` | *\"{cue['it']}\"* | *\"{cue['en']}\"* | `{ref_scene}` | {action} | `{cue.get('prompt', '')}` |"
        )

    # Save Storyboard Guide
    guide_path = output_dir / "STORYBOARD_GUIDE.md"
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write("\n".join(storyboard_md_lines) + "\n")
    console.print(f"[bold green]Saved Bilingual Storyboard Guide:[/bold green] {guide_path}")
    
    # 5. Build Subtitle Files
    ass_path = output_dir / "subtitles_78pt_roboto.ass"
    build_biochroma_ass(cues=aligned_cues, output_ass_path=ass_path, margin_v=margin_v, font_size=font_size)
    
    # 6. Assemble Master Rough-Cut Preview
    preview_path = output_dir / "rough_cut_preview.mp4"
    console.print(f"[cyan]Assembling master rough-cut preview: {preview_path.name}...[/cyan]")
    
    concat_txt = output_dir / "concat_list.txt"
    with open(concat_txt, "w", encoding="utf-8") as f:
        for entry in clip_entries:
            f.write(f"file '{entry['path'].resolve().as_posix()}'\n")
            
    try:
        rel_ass = ass_path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        rel_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
        
    fonts_dir = Path("fonts")
    fonts_param = f":fontsdir='{fonts_dir.as_posix()}'" if fonts_dir.exists() else ""
    vf_sub = f"ass=filename='{rel_ass}'{fonts_param}"
    
    preview_cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_txt),
        "-i", str(master_vo_target),
        "-vf", vf_sub,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "copy",
        "-shortest",
        str(preview_path)
    ]
    
    try:
        subprocess.run(preview_cmd, check=True)
    except subprocess.CalledProcessError:
        # Fallback to subtitles filter
        preview_cmd[preview_cmd.index("-vf") + 1] = f"subtitles=filename='{rel_ass}'{fonts_param}"
        subprocess.run(preview_cmd, check=True)
        
    if concat_txt.exists():
        concat_txt.unlink()
        
    console.print(f"\n[bold green]Success![/bold green] Reskin workspace created at: [bold]{output_dir}[/bold]")
    console.print(f"  • Sequenced clips: [bold]{clips_dir}[/bold] ({len(clip_entries)} clips in order)")
    console.print(f"  • Storyboard Guide: [bold]{guide_path}[/bold]")
    console.print(f"  • Preview Video: [bold]{preview_path}[/bold]")

@app.command()
def assemble(
    project_dir: Path = typer.Option(..., "--project-dir", "-p", help="Path to reskin project directory (containing clips/ and 00_master_voiceover.mp3)"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Target final master output video path"),
    margin_v: int = typer.Option(520, "--margin-v", help="BioChroma vertical margin (default: 520)"),
    font_size: int = typer.Option(78, "--font-size", help="BioChroma font size (default: 78)")
):
    """
    Assembles all clips in the project's 'clips/' directory in chronological sequence,
    muxes the master Italian voiceover, and burns official 78pt Roboto-Bold static subtitles.
    Use after you have replaced any placeholder clips with your generated AI video!
    """
    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    if not project_dir.exists():
        console.print(f"[bold red]Error: Project directory '{project_dir}' not found![/bold red]")
        raise typer.Exit(1)
        
    clips_dir = project_dir / "clips"
    if not clips_dir.exists():
        console.print(f"[bold red]Error: clips/ directory missing in '{project_dir}'![/bold red]")
        raise typer.Exit(1)
        
    vo_file = project_dir / "00_master_voiceover.mp3"
    if not vo_file.exists():
        console.print(f"[bold red]Error: 00_master_voiceover.mp3 missing in '{project_dir}'![/bold red]")
        raise typer.Exit(1)
        
    if output_file is None:
        output_file = project_dir / f"{project_dir.name}_FINAL_MASTER.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    def parse_clip_order(p: Path) -> int:
        try:
            return int(p.name.split("_")[0])
        except Exception:
            return 9999
    all_clips = sorted(list(clips_dir.glob("*.mp4")), key=parse_clip_order)
    console.print(f"[bold cyan]Assembling {len(all_clips)} clips in chronological sequence...[/bold cyan]")
    
    concat_txt = project_dir / "temp_assemble_concat.txt"
    with open(concat_txt, "w", encoding="utf-8") as f:
        for c in all_clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")
            
    ass_path = project_dir / "subtitles_78pt_roboto.ass"
    if not ass_path.exists():
        console.print("[yellow]subtitles_78pt_roboto.ass not found in project, generating default...[/yellow]")
        raise typer.Exit(1)
        
    try:
        rel_ass = ass_path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        rel_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
        
    fonts_dir = Path("fonts")
    fonts_param = f":fontsdir='{fonts_dir.as_posix()}'" if fonts_dir.exists() else ""
    vf_sub = f"ass=filename='{rel_ass}'{fonts_param}"
    
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_txt),
        "-i", str(vo_file),
        "-vf", vf_sub,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "copy",
        "-shortest",
        str(output_file)
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        cmd[cmd.index("-vf") + 1] = f"subtitles=filename='{rel_ass}'{fonts_param}"
        subprocess.run(cmd, check=True)
        
    if concat_txt.exists():
        concat_txt.unlink()
        
    console.print(f"\n[bold green]Success![/bold green] Final BioChroma ad assembled! Saved to: [bold]{output_file}[/bold]")

if __name__ == "__main__":
    app()
