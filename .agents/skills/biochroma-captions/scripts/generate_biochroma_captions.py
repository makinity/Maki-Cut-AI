#!/usr/bin/env python3
"""
BioChroma Ad Captioning Engine.
Autonomous, standardized caption generator for client BioChroma video ads.
Enforces 78pt Roboto-Bold, static non-kinetic layout, MarginV 520 (lower-middle safe zone),
strict single-line row (WrapStyle: 2), verbatim DP alignment, and bit-exact audio passthrough.
"""

import sys
import os
import re
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Default official BioChroma Italian Ad Chunks (optimized for single-row 78pt rendering)
DEFAULT_BIOCHROMA_CHUNKS = [
    # 01
    "Siamo entrati in casa",
    "e i suoi occhi sono andati",
    "dritti a lei.",
    # 02
    "Lo stesso sguardo che aveva per me",
    "quando avevo la metà dei miei anni.",
    # 03
    "L’ho odiata a prima vista.",
    "Ho pensato: “Ovvio, è fatta così.”",
    # 04
    "Poi ha sorriso, era dolce,",
    "ma in qualche modo è stato peggio.",
    # 05
    "Ha posato la borsa accanto a me",
    "ed è scesa di sotto con lui.",
    # 06
    "Ho alzato gli occhi al cielo",
    "e ho guardato altrove,",
    "poi ho visto qualcosa...",
    # 07
    "Una piccola fiala",
    "con dei fili dorati",
    "che spuntava dalla borsa.",
    # 08
    "E all’improvviso mi sono chiesta",
    "se fosse tutto qui.",
    # 09
    "Forse non era botox,",
    "forse non era l’età.",
    # 10
    "Forse il motivo per cui",
    "lui continuava a guardarla",
    "era lì, in quella borsa.",
    # 11
    "Ne ho presa una per me...",
    "L’ho messa quella sera",
    # 12
    "e al mattino",
    "quasi non mi riconoscevo...",
    # 13
    "Lui è sceso dalle scale",
    "e i suoi occhi sono andati",
    "dritti a me.",
    # 14
    "Strano come il giorno prima",
    "avessi dato tutta la colpa a lei.",
    # 15
    "Ho detto: “Non è niente, amore,",
    "ho solo dormito bene.”",
    # 16
    "BioChroma.",
    "Il nostro piccolo segreto.",
    # 17
    "In macchina, andando al lavoro,",
    "ho chiamato mia sorella.",
    # 18
    "Ho detto:",
    "“Non crederai a cosa ho fatto.",
    # 19
    "Ho rubato una fiala",
    "a quell’agente immobiliare",
    # 20
    "e all’improvviso mi ha guardata",
    "come se non esistesse",
    "nessun’altra donna.”",
    # 21
    "Lei ha riso:",
    "“Sei un’idiota, tesoro,",
    "è un siero ai peptidi di seta.",
    # 22
    "I Peptidi Dorati",
    "vengono dalla seta grezza",
    "del baco da seta coreano,",
    "usata da secoli",
    "nella medicina tradizionale",
    "coreana.",
    # 23
    "E il collagene",
    "a basso peso molecolare",
    "li porta attraverso",
    "lo strato corneo,",
    "abbastanza piccoli",
    "da entrare davvero nella pelle.”",
    # 24
    "Ho detto:",
    "“Quindi non ci stava provando?”",
    # 25
    "Ha detto: “Ma va, era solo gentile.”",
    # 26
    "A quanto pare",
    "ho odiato quella poverina",
    "per un siero",
    "che lavora mentre dormi.",
    # 27
    "Ha detto:",
    "“BioChroma è quello buono.”",
    # 28
    "Ho detto: “Mandami il link.”",
    # 29
    "Ne ho comprate due",
    "prima che scattasse il verde.",
    "Non ho nemmeno dovuto pensarci.",
    # 30
    "L’ho messo una sera",
    "e ho sentito subito un tiraggio,",
    "come se la pelle",
    "si sollevasse da dentro...",
    # 31
    "La mattina dopo",
    "quasi non mi riconoscevo...",
    "quasi non mi riconoscevo.",
    # 32
    "Lui è sceso dalle scale",
    "e i suoi occhi sono andati",
    "dritti a me.",
    # 33
    "Strano come il giorno prima",
    "avessi dato tutta la colpa a lei.",
    # 34
    "Ho detto: “Non è niente, amore,",
    "ho solo dormito bene.”",
    # 35
    "BioChroma.",
    "Il nostro piccolo segreto.",
    # 36
    "Mi ha detto: “Stai benissimo.",
    "Cosa ti sei messa?”",
    # 37
    "L’ho guardato e ho sorriso",
    "come se non fosse",
    "successo niente...",
    # 38
    "E da qualche parte",
    "quella poverina pensa ancora",
    "che io sia dolce,",
    # 39
    "mentre il suo siero",
    "ha quasi scatenato",
    "la Terza Guerra Mondiale.",
    # 40
    "BioChroma,",
    "il nostro piccolo segreto."
]

def get_ffmpeg_paths():
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def transcribe_audio_words(video_path: Path, model_size: str = "base") -> List[Dict[str, Any]]:
    from faster_whisper import WhisperModel
    print(f"Transcribing '{video_path.name}' using faster-whisper ({model_size} model, CPU int8)...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(video_path), word_timestamps=True, vad_filter=True)
    
    words = []
    for seg in segments:
        for w in seg.words:
            cleaned = w.word.strip()
            if cleaned:
                words.append({
                    "word": cleaned,
                    "start": round(w.start, 2),
                    "end": round(w.end, 2),
                    "probability": round(w.probability, 3)
                })
    print(f"Extracted {len(words)} timestamped words from audio.")
    return words

def norm_word(w: str) -> str:
    w = re.sub(r"[^\w]", "", w.lower())
    subs = {
        'diata': 'odiata',
        'pensa': 'pensato',
        'assorriso': 'sorriso',
        'sussiero': 'siero',
        'sierro': 'siero',
        'creo': 'biochroma',
        'credo': 'biochroma',
        'biocro': 'biochroma',
        'peghetto': 'segreto',
        'peppiti': 'peptidi',
        'colate': 'collagene',
        'vengrare': 'entrare',
        'boto': 'botox',
        'let': 'età',
        'schiale': 'scale',
        'dati': 'andati',
    }
    return subs.get(w, w)

def align_script_to_whisper(chunks: List[str], whisper_words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    script_words = []
    for c_idx, c in enumerate(chunks):
        tokens = re.findall(r"[\wÀ-ÿ]+(?:'[’\wÀ-ÿ]+)?", c)
        for t in tokens:
            script_words.append({
                "chunk_idx": c_idx,
                "raw": t,
                "norm": norm_word(t)
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
            script_timing[idx] = {"start": round(interp_t, 2), "end": round(interp_t + 0.25, 2)}

    # Build raw chunk intervals
    raw_chunks = []
    for c_idx, c in enumerate(chunks):
        c_indices = [idx for idx, sw in enumerate(script_words) if sw['chunk_idx'] == c_idx]
        s_t = script_timing[c_indices[0]]['start']
        e_t = script_timing[c_indices[-1]]['end']
        if e_t <= s_t:
            e_t = s_t + 0.6
        raw_chunks.append({
            "chunk_idx": c_idx,
            "text": c,
            "start": s_t,
            "end": e_t
        })

    # Enforce minimum 0.6s display duration
    for c in raw_chunks:
        if c['end'] - c['start'] < 0.6:
            c['end'] = c['start'] + 0.6

    # Prevent overlaps
    for idx in range(len(raw_chunks) - 1):
        c1 = raw_chunks[idx]
        c2 = raw_chunks[idx+1]
        if c1['end'] > c2['start']:
            if c2['start'] - c1['start'] >= 0.6:
                c1['end'] = c2['start']
            else:
                c1['end'] = c1['start'] + 0.6
                c2['start'] = max(c2['start'], c1['end'])
                if c2['end'] < c2['start'] + 0.6:
                    c2['end'] = c2['start'] + 0.6

    # Bridge small gaps (< 0.22s) and pad speech decay
    for idx in range(len(raw_chunks) - 1):
        c1 = raw_chunks[idx]
        c2 = raw_chunks[idx+1]
        gap = c2['start'] - c1['end']
        if 0 < gap < 0.22:
            c1['end'] = c2['start']
        elif gap >= 0.22:
            max_pad = gap - 0.08
            if max_pad > 0:
                c1['end'] = min(c1['end'] + 0.12, c1['end'] + max_pad)

    raw_chunks[-1]['end'] = round(raw_chunks[-1]['end'] + 0.5, 2)
    return raw_chunks

def format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs == 100:
        s += 1
        cs = 0
        if s == 60:
            m += 1
            s = 0
            if m == 60:
                h += 1
                m = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
        if s == 60:
            m += 1
            s = 0
            if m == 60:
                h += 1
                m = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def generate_biochroma_ass_and_srt(
    chunks: List[Dict[str, Any]],
    ass_path: Path,
    srt_path: Path,
    font_size: int = 78,
    outline_width: float = 4.0,
    margin_v: int = 520
):
    ass_header = f"""[Script Info]
; Script generated by BioChroma Caption Engine
Title: BioChroma Italian Ad Subtitles
ScriptType: v4.00+
WrapStyle: 2
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Roboto,{font_size},&H00FFFFFF,&H000000FF,&H00181818,&H00000000,-1,0,0,0,100,100,0.5,0,1,{outline_width},0,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass_lines = []
    srt_lines = []

    for idx, c in enumerate(chunks):
        s_ass = format_ass_time(c['start'])
        e_ass = format_ass_time(c['end'])
        ass_lines.append(f"Dialogue: 0,{s_ass},{e_ass},Default,,0,0,{margin_v},,{c['text']}")

        s_srt = format_srt_time(c['start'])
        e_srt = format_srt_time(c['end'])
        srt_lines.append(f"{idx+1}\n{s_srt} --> {e_srt}\n{c['text']}\n")

    ass_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.parent.mkdir(parents=True, exist_ok=True)

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(ass_lines) + "\n")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    print(f"Generated ASS: {ass_path} ({len(chunks)} events, Fontsize={font_size}, MarginV={margin_v})")
    print(f"Generated SRT: {srt_path}")

def render_captioned_video(
    input_video: Path,
    ass_path: Path,
    output_video: Path,
    fonts_dir: Path
):
    ffmpeg_exe, _ = get_ffmpeg_paths()
    # Format filter paths cleanly using relative paths where possible to avoid Windows colon issues
    try:
        rel_ass = ass_path.relative_to(Path.cwd())
        ass_arg = str(rel_ass).replace("\\", "/")
    except ValueError:
        ass_arg = str(ass_path).replace("\\", "/").replace(":", "\\:")

    try:
        rel_fonts = fonts_dir.relative_to(Path.cwd())
        fonts_arg = str(rel_fonts).replace("\\", "/")
    except ValueError:
        fonts_arg = str(fonts_dir).replace("\\", "/").replace(":", "\\:")

    vf_filter = f"subtitles='{ass_arg}':fontsdir='{fonts_arg}'" if " " in ass_arg or " " in fonts_arg else f"subtitles={ass_arg}:fontsdir={fonts_arg}"
    if sys.platform == "win32":
        # Simpler and robust on Windows:
        vf_filter = f"subtitles={ass_arg}:fontsdir={fonts_arg}"

    nvenc_cmd = [
        ffmpeg_exe, "-y",
        "-i", str(input_video),
        "-vf", vf_filter,
        "-c:v", "h264_nvenc",
        "-preset", "p5",
        "-cq", "19",
        "-b:v", "0",
        "-c:a", "copy",
        str(output_video)
    ]

    print(f"Rendering video with hardware acceleration (NVENC): {output_video.name}...")
    res = subprocess.run(nvenc_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("NVENC encoder failed or unavailable, falling back to libx264...")
        cpu_cmd = [
            ffmpeg_exe, "-y",
            "-i", str(input_video),
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(output_video)
        ]
        res_cpu = subprocess.run(cpu_cmd, capture_output=True, text=True)
        if res_cpu.returncode != 0:
            print("FFmpeg error:", res_cpu.stderr)
            sys.exit(1)

    print(f"Render complete: {output_video} (Size: {output_video.stat().st_size / (1024*1024):.1f} MB)")

def main():
    parser = argparse.ArgumentParser(description="BioChroma Ad Captioning Engine")
    parser.add_argument("-i", "--input", type=str, help="Input video path (defaults to newest .mp4 in Input/)")
    parser.add_argument("-o", "--output", type=str, help="Output captioned video path (defaults to Output/<basename>_captioned.mp4)")
    parser.add_argument("--script-file", type=str, help="Optional text file with verbatim script chunks (defaults to built-in BioChroma Italian chunks)")
    parser.add_argument("--font-size", type=int, default=78, help="Font size in pt (default: 78)")
    parser.add_argument("--outline-width", type=float, default=4.0, help="Outline border width (default: 4.0)")
    parser.add_argument("--margin-v", type=int, default=520, help="Vertical margin from bottom edge (default: 520, ~27%)")
    parser.add_argument("--fonts-dir", type=str, default="fonts", help="Fonts directory path (default: fonts)")
    parser.add_argument("--skip-render", action="store_true", help="Generate ASS and SRT files only without rendering video")
    args = parser.parse_args()

    project_root = Path.cwd()
    input_dir = project_root / "Input"
    output_dir = project_root / "Output"
    fonts_dir = Path(args.fonts_dir) if Path(args.fonts_dir).is_absolute() else project_root / args.fonts_dir

    # Find input video
    if args.input:
        input_video = Path(args.input)
    else:
        mp4_files = sorted(input_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not mp4_files:
            print("Error: No .mp4 files found in Input/. Please provide -i <PATH>.")
            sys.exit(1)
        input_video = mp4_files[0]
        print(f"Auto-selected latest input video: {input_video.name}")

    if not input_video.exists():
        print(f"Error: Input video not found at {input_video}")
        sys.exit(1)

    # Determine output paths
    base_stem = input_video.stem.replace(" ", "_")
    output_video = Path(args.output) if args.output else output_dir / f"{base_stem}_captioned.mp4"
    ass_path = output_dir / f"{base_stem}_subtitles.ass"
    srt_path = output_dir / f"{base_stem}_subtitles.srt"

    # Load chunks
    if args.script_file and Path(args.script_file).exists():
        with open(args.script_file, "r", encoding="utf-8") as f:
            chunks = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        print(f"Loaded {len(chunks)} chunks from {args.script_file}")
    else:
        chunks = DEFAULT_BIOCHROMA_CHUNKS
        print(f"Using default BioChroma Italian chunks ({len(chunks)} lines).")

    # Transcribe & align
    whisper_words = transcribe_audio_words(input_video, model_size="base")
    aligned_chunks = align_script_to_whisper(chunks, whisper_words)

    # Generate ASS & SRT
    generate_biochroma_ass_and_srt(
        aligned_chunks,
        ass_path,
        srt_path,
        font_size=args.font_size,
        outline_width=args.outline_width,
        margin_v=args.margin_v
    )

    # Render video
    if not args.skip_render:
        render_captioned_video(input_video, ass_path, output_video, fonts_dir)

if __name__ == "__main__":
    main()

