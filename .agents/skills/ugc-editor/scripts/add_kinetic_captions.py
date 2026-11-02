#!/usr/bin/env python3
"""
Kinetic Captions & Context PinPoint Emphasis Generator for UGC Videos.
Produces word-level animated subtitles with kinetic pop-in and keyword emphasis (Hormozi / TikTok style).
"""

import sys
import os
import re
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import typer
from rich.console import Console

app = typer.Typer(help="Generate kinetic captions with context pinpoint emphasis.")
console = Console()

# Built-in high-impact context pinpoint keywords
DEFAULT_PINPOINTS = {
    "stop", "secret", "never", "always", "proven", "best", "worst", "free",
    "money", "cash", "dollars", "results", "insane", "crazy", "fast", "easy",
    "hack", "trick", "watch", "look", "how", "why", "what", "boom", "alert",
    "mistake", "warning", "guaranteed", "truth", "revealed", "simple", "huge"
}

def get_ffmpeg_paths():
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
    """
    Transcribe audio using faster-whisper with word-level timestamps.
    """
    from faster_whisper import WhisperModel
    
    console.print(f"[cyan]Transcribing audio using faster-whisper ({model_size} model)...[/cyan]")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(video_path), word_timestamps=True, vad_filter=True)
    
    words_data = []
    for segment in segments:
        for word in segment.words:
            # Clean word text
            cleaned_word = word.word.strip()
            if cleaned_word:
                words_data.append({
                    "word": cleaned_word,
                    "start": word.start,
                    "end": word.end,
                    "probability": word.probability
                })
    console.print(f"[green]Extracted {len(words_data)} words with microsecond timestamps.[/green]")
    return words_data

def chunk_words(words: List[Dict[str, Any]], max_words: int = 3) -> List[List[Dict[str, Any]]]:
    """
    Group words into small UGC chunks (1-3 words) for fast, engaging readability.
    """
    chunks = []
    current_chunk = []
    
    for i, w in enumerate(words):
        current_chunk.append(w)
        # End chunk if max words reached or there is a natural pause (> 0.4s)
        time_to_next = (words[i+1]["start"] - w["end"]) if i + 1 < len(words) else 1.0
        if len(current_chunk) >= max_words or time_to_next > 0.35 or w["word"].endswith(('.', '!', '?')):
            chunks.append(current_chunk)
            current_chunk = []
            
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

def build_ass_subtitle(
    chunks: List[List[Dict[str, Any]]],
    output_ass_path: Path,
    pinpoints: set,
    style_name: str = "hormozi"
):
    """
    Construct an ASS subtitle file with kinetic pop-in and context pinpoint emphasis.
    """
    # Color definitions in ASS &HAABBGGRR& format
    # In ASS, color format is &H[Alpha][Blue][Green][Red]&
    if style_name == "neon_green":
        highlight_color = "&H0014FF39&"  # Neon Green
        pinpoint_color = "&H0000E5FF&"   # Electric Yellow
    elif style_name == "clean_white":
        highlight_color = "&H0000E5FF&"  # Electric Yellow
        pinpoint_color = "&H001050FF&"   # Hot Red
    else: # "hormozi" (Default popular UGC look)
        highlight_color = "&H0000FFFF&"  # Bright Yellow
        pinpoint_color = "&H0014FF39&"   # Neon Green PinPoint

    normal_color = "&H00FFFFFF&"
    outline_color = "&H00000000&"
    
    # ASS Header
    ass_content = f"""[Script Info]
Title: UGC Kinetic Captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,88,{normal_color},&H000000FF&,{outline_color},&H80000000&,-1,0,0,0,100,100,2,0,1,10,4,2,60,60,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    events = []
    
    for chunk in chunks:
        if not chunk:
            continue
        chunk_start = chunk[0]["start"]
        chunk_end = chunk[-1]["end"]
        
        # Display each active word pop-in as time progresses within the chunk
        for active_idx, active_word in enumerate(chunk):
            w_start = active_word["start"]
            # Active word duration or until next word starts
            w_end = chunk[active_idx + 1]["start"] if active_idx + 1 < len(chunk) else chunk_end
            
            # Build styled string for this micro-frame
            word_elements = []
            for idx, word_obj in enumerate(chunk):
                raw_text = word_obj["word"].upper()
                is_clean_word = re.sub(r'[^a-zA-Z0-9]', '', raw_text.lower())
                is_pinpoint = (is_clean_word in pinpoints) or any(c in "$%#0123456789" for c in raw_text)
                
                if idx == active_idx:
                    # Current active spoken word: Kinetic Pop Scale + Bright Accent
                    if is_pinpoint:
                        # PinPoint emphasis: Huge Pop (125%) + Pinpoint Accent Color
                        word_str = f"{{\\c{pinpoint_color}\\t(0,120,\\fscx125\\fscy125)}}{raw_text}{{\\r}}"
                    else:
                        # Standard active pop (112%) + Highlight Color
                        word_str = f"{{\\c{highlight_color}\\t(0,100,\\fscx115\\fscy115)}}{raw_text}{{\\r}}"
                else:
                    # Inactive word in current chunk
                    if is_pinpoint:
                        word_str = f"{{\\c{pinpoint_color}}}{raw_text}{{\\r}}"
                    else:
                        word_str = f"{{\\c{normal_color}}}{raw_text}{{\\r}}"
                        
                word_elements.append(word_str)
                
            line_text = " ".join(word_elements)
            ass_line = f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},Default,,0,0,0,,{line_text}"
            events.append(ass_line)
            
    ass_content += "\n".join(events) + "\n"
    
    output_ass_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)
        
    console.print(f"[bold green]Saved ASS subtitles:[/bold green] {output_ass_path}")

@app.command()
def generate_captions(
    input_file: Path = typer.Option(..., "--input", "-i", help="Path to input video (in Input/ or Output/)"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Path to output video with burned-in kinetic captions"),
    pinpoints: Optional[str] = typer.Option(None, "--pinpoints", "-p", help="Comma-separated context emphasis keywords (e.g. 'secret,money,proven')"),
    style: str = typer.Option("hormozi", "--style", "-s", help="Caption visual style: 'hormozi', 'neon_green', 'clean_white'"),
    words_per_line: int = typer.Option(3, "--max-words", "-w", help="Maximum words displayed per chunk (1-4)"),
    model_size: str = typer.Option("base", "--model", "-m", help="Whisper model size: tiny, base, small"),
    burn_in: bool = typer.Option(True, "--burn/--no-burn", help="Burn captions directly into video")
):
    """
    Generates word-level accurate kinetic captions with context pinpoint emphasis.
    """
    ffmpeg_exe, _ = get_ffmpeg_paths()
    
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file '{input_file}' not found![/bold red]")
        raise typer.Exit(1)
        
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if output_file is None:
        output_file = output_dir / f"{input_file.stem}_captioned.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    ass_path = output_dir / f"{input_file.stem}_captions.ass"
    
    # 1. Prepare PinPoint keyword list
    emphasis_words = set(DEFAULT_PINPOINTS)
    if pinpoints:
        custom_words = [w.strip().lower() for w in pinpoints.split(",") if w.strip()]
        emphasis_words.update(custom_words)
    console.print(f"[cyan]Active context pinpoint triggers: [bold]{len(emphasis_words)}[/bold] keywords & numbers.[/cyan]")

    # 2. Transcribe with word timestamps
    words = transcribe_audio(input_file, model_size=model_size)
    if not words:
        console.print("[yellow]Warning: No speech detected in video audio stream.[/yellow]")
        return
        
    # 3. Chunk words into short UGC phrases
    chunks = chunk_words(words, max_words=words_per_line)
    console.print(f"[cyan]Created {len(chunks)} kinetic subtitle phrases ({words_per_line} words/line).[/cyan]")

    # 4. Build ASS subtitle file
    build_ass_subtitle(chunks, ass_path, emphasis_words, style_name=style)

    # 5. Burn-in via FFmpeg if requested
    if burn_in:
        console.print("[cyan]Burning kinetic captions into video via FFmpeg...[/cyan]")
        # Escape path for FFmpeg subtitles filter on Windows
        rel_ass = str(ass_path.as_posix())
        
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", str(input_file),
            "-vf", f"ass='{rel_ass}'",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "copy",
            str(output_file)
        ]
        
        try:
            subprocess.run(cmd, check=True)
            console.print(f"\n[bold green]Success![/bold green] Video with kinetic captions saved to: [bold]{output_file}[/bold]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]FFmpeg burn-in failed: {e}[/red]")
            console.print("[yellow]Falling back to standard subtitles filter...[/yellow]")
            cmd[4] = f"subtitles='{rel_ass}'"
            subprocess.run(cmd, check=True)
            console.print(f"\n[bold green]Success![/bold green] Saved to: [bold]{output_file}[/bold]")

if __name__ == "__main__":
    app()

