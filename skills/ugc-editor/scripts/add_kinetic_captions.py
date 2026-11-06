#!/usr/bin/env python3
"""
Next-Gen UGC Kinetic Captions & Tier-1 Headline Label Engine.
Dual-layer system:
  Layer 1: Continuous Lower-Third subtitles with kinetic word pop & highlight.
  Layer 2: High-impact Tier-1 Headline Labels with elastic spring-physics animation,
           strict cooldown spacing (max 3-4 per video), and face-safe positioning (Top Safe Zone / Chest).
"""

import sys
import os
import re
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
import typer
from rich.console import Console

# UTF-8 resilience for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(help="Generate kinetic captions with face-safe Tier-1 headline labels.")
console = Console()

# Curated Tier-1 Impact Patterns: Physical/somatic symptoms, dramatic numbers/times, shock hooks
TIER1_PATTERNS = [
    # Physical/somatic symptoms & emotional states
    r"\b(jaws?|teeth|clenching|clenched)\b",
    r"\b(floor|ground|collapsed?|paralyzed?|frozen)\b",
    r"\b(burnouts?|exhaust(ed|ion)|drained)\b",
    r"\b(anxiety|panic|heart racing|can't breathe|chest tight)\b",
    r"\b(shaking|trembl(e|ing)|sweat(ing)?|numb)\b",
    r"\b(dysregulated|nervous system|trauma|dissociat(e|ed|ion))\b",
    r"\b(migraines?|headaches?|chronic pain|insomnia)\b",
    # Concrete numbers, durations & shocking metrics
    r"\b(\d+\s*(minutes?|hours?|days?|weeks?|months?|years?))\b",
    r"\b(thirty|twenty|fifteen|ten|five)\s+(minutes?|hours?|years?)\b",
    r"\b(thousands|hundreds|millions)\s+of\b",
    r"\b(10x|100%|zero|half|double)\b",
    r"\b(\$\d+[\d,]*|\d+\s*dollars?)\b",
    # Powerful hooks & reveals
    r"\b(stop scrolling|warning|secret|exposed|truth revealed|game changer)\b",
    r"\b(biggest mistake|never do this|worst thing)\b"
]

def get_ffmpeg_paths() -> Tuple[str, str]:
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp format: H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def transcribe_audio(video_path: Path, model_size: str = "base") -> List[Dict[str, Any]]:
    """Transcribe audio using faster-whisper with word-level microsecond timestamps."""
    from faster_whisper import WhisperModel
    
    console.print(f"[cyan]Transcribing audio using faster-whisper ({model_size} model)...[/cyan]")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(video_path), word_timestamps=True, vad_filter=True)
    
    words_data = []
    for segment in segments:
        for word in segment.words:
            cleaned_word = word.word.strip()
            if cleaned_word:
                words_data.append({
                    "word": cleaned_word,
                    "start": word.start,
                    "end": word.end,
                    "probability": word.probability
                })
    console.print(f"[green]Extracted {len(words_data)} spoken words with microsecond precision.[/green]")
    return words_data

def chunk_words(words: List[Dict[str, Any]], max_words: int = 3) -> List[List[Dict[str, Any]]]:
    """Group words into punchy UGC phrases (1-3 words per subtitle event)."""
    chunks = []
    current_chunk = []
    
    for i, w in enumerate(words):
        current_chunk.append(w)
        time_to_next = (words[i+1]["start"] - w["end"]) if i + 1 < len(words) else 1.0
        if len(current_chunk) >= max_words or time_to_next > 0.35 or w["word"].endswith(('.', '!', '?')):
            chunks.append(current_chunk)
            current_chunk = []
            
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

def detect_tier1_headlines(
    words: List[Dict[str, Any]],
    user_pinpoints: Optional[List[str]] = None,
    max_headlines: int = 4,
    min_cooldown: float = 9.0
) -> List[Dict[str, Any]]:
    """
    Identifies high-impact Tier-1 headline moments and strictly enforces:
      - Max count (default: 3-4 per video)
      - Minimum breathing room cooldown (e.g. 9s)
      - Automatic Hook 1 detection (first 3.5s)
    """
    full_text = " ".join(w["word"] for w in words)
    console.print(f"[cyan]Analyzing speech for Tier-1 headline moments...[/cyan]")
    
    candidate_events = []
    
    # 1. Guaranteed Opening Hook (First 0.0s - 3.5s)
    hook_words = [w for w in words if w["start"] <= 3.8]
    if hook_words:
        hook_text = " ".join(w["word"] for w in hook_words[:6]).upper()
        # Clean punctuation
        hook_clean = re.sub(r'[,.!?]', '', hook_text)
        # Split into max 2 balanced lines
        words_in_hook = hook_clean.split()
        if len(words_in_hook) >= 4:
            mid = len(words_in_hook) // 2
            formatted_hook = " ".join(words_in_hook[:mid]) + "\\N" + " ".join(words_in_hook[mid:])
        else:
            formatted_hook = " ".join(words_in_hook)
            
        candidate_events.append({
            "start": max(0.2, hook_words[0]["start"]),
            "end": min(hook_words[-1]["end"] + 0.3, 3.8),
            "text": formatted_hook,
            "score": 100,  # Highest priority
            "type": "hook"
        })

    # 2. Custom User Pinpoints (High Priority)
    if user_pinpoints:
        for pin in user_pinpoints:
            pin_clean = pin.strip().lower()
            if not pin_clean:
                continue
            # Search for consecutive matching words
            pin_tokens = pin_clean.split()
            for i in range(len(words) - len(pin_tokens) + 1):
                window = [re.sub(r'[^a-zA-Z0-9]', '', words[i+j]["word"].lower()) for j in range(len(pin_tokens))]
                target = [re.sub(r'[^a-zA-Z0-9]', '', t) for t in pin_tokens]
                if window == target:
                    start_t = words[i]["start"]
                    end_t = words[i + len(pin_tokens) - 1]["end"] + 0.4
                    # Duration between 1.6s and 2.6s
                    duration = max(1.8, min(end_t - start_t, 2.6))
                    
                    label_raw = pin.upper()
                    if len(pin_tokens) >= 4:
                        mid = len(pin_tokens) // 2
                        label_fmt = " ".join(pin_tokens[:mid]).upper() + "\\N" + " ".join(pin_tokens[mid:]).upper()
                    else:
                        label_fmt = label_raw
                        
                    candidate_events.append({
                        "start": start_t,
                        "end": start_t + duration,
                        "text": label_fmt,
                        "score": 90,
                        "type": "user_pinpoint"
                    })

    # 3. Built-in Tier-1 Patterns (Somatic Symptoms & Metrics)
    for pattern in TIER1_PATTERNS:
        for match in re.finditer(pattern, full_text, flags=re.IGNORECASE):
            matched_phrase = match.group(0).strip()
            # Find matching word timestamps
            phrase_clean = re.sub(r'[^a-zA-Z0-9\s]', '', matched_phrase.lower()).split()
            if not phrase_clean:
                continue
            for i in range(len(words) - len(phrase_clean) + 1):
                window = [re.sub(r'[^a-zA-Z0-9]', '', words[i+j]["word"].lower()) for j in range(len(phrase_clean))]
                if window == phrase_clean:
                    start_t = words[i]["start"]
                    end_t = words[i + len(phrase_clean) - 1]["end"] + 0.4
                    duration = max(1.8, min(end_t - start_t, 2.4))
                    
                    # Expand context slightly if single word (e.g. "jaws" -> "CLENCHED JAWS")
                    if len(phrase_clean) == 1 and i > 0 and words[i-1]["word"].lower() in {"clenched", "tight", "locking"}:
                        label_fmt = f"{words[i-1]['word'].upper()}\\N{matched_phrase.upper()}"
                        start_t = words[i-1]["start"]
                    else:
                        if len(phrase_clean) >= 4:
                            mid = len(phrase_clean) // 2
                            label_fmt = " ".join(phrase_clean[:mid]).upper() + "\\N" + " ".join(phrase_clean[mid:]).upper()
                        else:
                            label_fmt = matched_phrase.upper()
                            
                    candidate_events.append({
                        "start": start_t,
                        "end": start_t + duration,
                        "text": label_fmt,
                        "score": 80,
                        "type": "tier1_symptom"
                    })
                    break

    # 4. Strict Filtering: Sort by time and apply Cooldown & Max Limit
    candidate_events.sort(key=lambda x: x["start"])
    
    selected_headlines = []
    last_end_time = -999.0
    
    for cand in candidate_events:
        # Check cooldown
        if (cand["start"] - last_end_time) >= min_cooldown:
            selected_headlines.append(cand)
            last_end_time = cand["end"]
            if len(selected_headlines) >= max_headlines:
                break
                
    console.print(f"[bold green]Curated {len(selected_headlines)} Tier-1 Headline Labels (max: {max_headlines}, min cooldown: {min_cooldown}s):[/bold green]")
    for h in selected_headlines:
        clean_name = h['text'].replace('\\N', ' ')
        console.print(f"  • [{h['start']:.2f}s - {h['end']:.2f}s] [bold yellow]{clean_name}[/bold yellow] ({h['type']})")
        
    return selected_headlines

def build_dual_layer_ass(
    chunks: List[List[Dict[str, Any]]],
    headlines: List[Dict[str, Any]],
    output_ass_path: Path,
    style_name: str = "brand_gold",
    headline_pos: str = "top",
    custom_headline_y: Optional[int] = None
):
    """
    Constructs an ASS subtitle file with two independent visual layers:
      1. LowerThird: Continuous spoken dialogue with word pop & active highlight.
      2. Headline: Bold Archivo Black kinetic labels with elastic spring-physics
                   positioned safely (Top Safe Zone Y=340 or Chest Y=1260).
    """
    # Color mapping: ASS format &HAABBGGRR&
    if style_name == "hormozi":
        accent_color = "&H0000FFFF&"   # Bright Yellow
        text_color = "&H00FFFFFF&"     # White
        headline_color = "&H0014FF39&" # Neon Green
        outline_color = "&H00000000&"  # Pure Black
        shadow_color = "&H80000000&"
    elif style_name == "clean_white":
        accent_color = "&H001050FF&"   # Hot Red
        text_color = "&H00FFFFFF&"
        headline_color = "&H0000E5FF&" # Electric Yellow
        outline_color = "&H00070707&"
        shadow_color = "&H80070707&"
    elif style_name == "neon_cyan":
        accent_color = "&H00FFFF00&"   # Electric Cyan
        text_color = "&H00FFFFFF&"
        headline_color = "&H00FF3399&" # Neon Magenta
        outline_color = "&H00070707&"
        shadow_color = "&H80070707&"
    else:  # "brand_gold" (Default premium UGC)
        accent_color = "&H004CABD6&"   # Gold #D6AB4C
        text_color = "&H00E8F0F4&"     # Cream #F4F0E8
        headline_color = "&H004CABD6&" # Gold #D6AB4C
        outline_color = "&H00070707&"  # Black #070707
        shadow_color = "&H9024333D&"   # Dark Brown #3D3324

    # Determine Safe Headline Y Position (Canvas 1080x1920)
    # Never dead-center Y=960!
    if custom_headline_y is not None:
        headline_y = custom_headline_y
    elif headline_pos == "chest":
        headline_y = 1260  # Upper chest, well below chin, above captions
    else:  # "top" (default)
        headline_y = 340   # Upper-third safe zone, well above forehead

    # Elastic spring pop animation for headlines (Overshoot 112% -> 96% -> 100%)
    # Clamped with smooth 180ms fade-out
    headline_anim = (
        f"{{\\pos(540,{headline_y})"
        r"\fscx75\fscy75"
        r"\t(0,80,\fscx112\fscy112)"
        r"\t(80,150,\fscx96\fscy96)"
        r"\t(150,220,\fscx100\fscy100)"
        r"\fad(0,180)}"
    )

    ass_content = f"""[Script Info]
Title: UGC Dual-Layer Kinetic Captions
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: LowerThird,Roboto Mono,68,{text_color},&H000000FF,{outline_color},{shadow_color},-1,0,0,0,100,100,0,0,1,5.0,2.0,2,30,30,420,1
Style: Headline,Archivo Black,110,{headline_color},&H000000FF,{outline_color},{shadow_color},-1,0,0,0,86,100,2,0,1,8.0,6.0,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []

    # 1. Render Layer 0: Continuous Lower-Third Captions
    for chunk in chunks:
        if not chunk:
            continue
        chunk_end = chunk[-1]["end"]
        
        for active_idx, active_word in enumerate(chunk):
            w_start = active_word["start"]
            w_end = chunk[active_idx + 1]["start"] if active_idx + 1 < len(chunk) else chunk_end
            if w_end <= w_start:
                w_end = w_start + 0.15
                
            line_parts = []
            for idx, word_obj in enumerate(chunk):
                raw = word_obj["word"].upper()
                if idx == active_idx:
                    # Active spoken word: Pop scale (115% -> 100%) + Accent Color
                    word_str = f"{{\\c{accent_color}\\t(0,90,\\fscx114\\fscy114)}}{raw}{{\\r}}"
                else:
                    word_str = f"{{\\c{text_color}}}{raw}{{\\r}}"
                line_parts.append(word_str)
                
            full_line = " ".join(line_parts)
            events.append(f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},LowerThird,,0,0,0,,{full_line}")

    # 2. Render Layer 1: High-Impact Tier-1 Headline Labels (Only 3-4 Curated Moments)
    for hl in headlines:
        h_start = format_ass_time(hl["start"])
        h_end = format_ass_time(hl["end"])
        text = f"{headline_anim}{hl['text']}"
        events.append(f"Dialogue: 1,{h_start},{h_end},Headline,,0,0,0,,{text}")

    ass_content += "\n".join(events) + "\n"

    output_ass_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    console.print(f"[bold green]Saved Dual-Layer ASS Subtitles:[/bold green] {output_ass_path}")

@app.command()
def generate_captions(
    input_file: Path = typer.Option(..., "--input", "-i", help="Path to input video (in Input/ or Output/)"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Path to output video with burned-in captions"),
    pinpoints: Optional[str] = typer.Option(None, "--pinpoints", "-p", help="Explicit keywords to feature in headline labels (e.g. 'jaws, 30 minutes on the floor')"),
    max_headlines: int = typer.Option(4, "--max-headlines", help="Strict limit on number of headline labels (default: 4, recommended: 3-4)"),
    cooldown: float = typer.Option(9.0, "--cooldown", help="Minimum cooldown seconds between headline labels (default: 9.0s)"),
    headline_pos: str = typer.Option("top", "--headline-pos", help="Face-safe headline position: 'top' (Y=340, above forehead) or 'chest' (Y=1260, below chin)"),
    headline_y: Optional[int] = typer.Option(None, "--headline-y", help="Exact custom Y coordinate for headline (e.g. 340, 1260)"),
    style: str = typer.Option("brand_gold", "--style", "-s", help="Visual style: 'brand_gold', 'hormozi', 'clean_white', 'neon_cyan'"),
    words_per_line: int = typer.Option(3, "--max-words", "-w", help="Words displayed per lower-third chunk (1-4)"),
    model_size: str = typer.Option("base", "--model", "-m", help="Whisper model: tiny, base, small"),
    burn_in: bool = typer.Option(True, "--burn/--no-burn", help="Burn captions directly into video")
):
    """
    Generates word-level accurate kinetic captions with face-safe Tier-1 headline labels.
    """
    ffmpeg_exe, _ = get_ffmpeg_paths()
    
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file '{input_file}' not found![/bold red]")
        raise typer.Exit(1)
        
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if output_file is None:
        output_file = output_dir / f"{input_file.stem}_kinetic_captioned.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    ass_path = output_dir / f"{input_file.stem}_captions.ass"
    
    # 1. Parse user pinpoints if provided
    user_pinpoints_list = [p.strip() for p in pinpoints.split(",")] if pinpoints else None

    # 2. Transcribe speech with microsecond timestamps
    words = transcribe_audio(input_file, model_size=model_size)
    if not words:
        console.print("[yellow]Warning: No speech detected in video audio stream.[/yellow]")
        return
        
    # 3. Chunk words into short Lower-Third UGC phrases
    chunks = chunk_words(words, max_words=words_per_line)
    console.print(f"[cyan]Created {len(chunks)} Lower-Third subtitle phrases ({words_per_line} words/line).[/cyan]")

    # 4. Detect and filter Tier-1 Headline Labels with strict spacing & cooldown
    headlines = detect_tier1_headlines(
        words,
        user_pinpoints=user_pinpoints_list,
        max_headlines=max_headlines,
        min_cooldown=cooldown
    )

    # 5. Build Dual-Layer ASS Subtitle File
    build_dual_layer_ass(
        chunks=chunks,
        headlines=headlines,
        output_ass_path=ass_path,
        style_name=style,
        headline_pos=headline_pos,
        custom_headline_y=headline_y
    )

    # 6. Burn-in via FFmpeg with Bit-Exact Audio Copy (-c:a copy)
    if burn_in:
        console.print("[cyan]Burning dual-layer kinetic captions into video via FFmpeg...[/cyan]")
        rel_ass = str(ass_path.as_posix())
        
        # Check fonts directory
        fonts_param = "fontsdir=fonts:" if Path("fonts").exists() else ""
        vf_filter = f"{fonts_param}ass='{rel_ass}'"
        
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", str(input_file),
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "copy",
            str(output_file)
        ]
        
        try:
            subprocess.run(cmd, check=True)
            console.print(f"\n[bold green]Success![/bold green] Video saved to: [bold]{output_file}[/bold]")
        except subprocess.CalledProcessError as e:
            console.print(f"[yellow]FFmpeg 'ass' filter fallback to 'subtitles'...[/yellow]")
            cmd[4] = f"{fonts_param}subtitles='{rel_ass}'"
            subprocess.run(cmd, check=True)
            console.print(f"\n[bold green]Success![/bold green] Saved to: [bold]{output_file}[/bold]")

if __name__ == "__main__":
    app()
