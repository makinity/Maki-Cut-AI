---
name: biochroma-captions
description: >-
  BioChroma Ad Subtitle Engine - Generates standardized, non-kinetic, single-row 78pt Roboto-Bold subtitles
  strictly adhering to client BioChroma specifications (lower-middle safe zone 27% / MarginV 520, verbatim
  Italian script DP alignment, WrapStyle 2, and bit-exact audio preservation).
---

# BioChroma Ad Captioning Engine

Standardized captioning skill for **Client BioChroma** video ads (TikTok, Instagram Reels, YouTube Shorts).
Whenever the user asks to **"put a caption for biochroma ad"**, **"caption this biochroma ad"**, or mentions **"BioChroma ad captions"**, this exact skill and setup must be used.

---

## Client BioChroma Style Specifications

| Property | Value / Specification | Why This Matters |
| :--- | :--- | :--- |
| **Font Family** | **Roboto Bold** (`Roboto-Bold.ttf`) | Clean, modern, highly legible sans-serif. |
| **Font Weight** | True Bold (`Bold: -1`) | Maximum contrast and readability on mobile devices. |
| **Font Size** | **`78 pt`** (on 1080×1920 reference canvas) | Client-approved prominent scale, easily readable without squinting. |
| **Text Color** | Pure White (`#FFFFFF`, `&H00FFFFFF&`) | High luminance contrast against video footage. |
| **Stroke / Outline** | **`4.0 pt`** dark stroke (`#181818`, `&H00181818&`) | Thin, crisp boundary that prevents text blending into light scenes. |
| **Shadow / Glow** | None (`Shadow: 0`) | Keeps text sharp and minimal without muddy halos. |
| **Letter Spacing** | `0.5 pt` | Prevents glyph collision in uppercase or bold text. |
| **Motion / Kinetic** | **Completely Static** | NO bounce, NO karaoke word-coloring, NO pop-up scale, NO fade transitions. Clean cuts only. |
| **Row Constraint** | **Strict Single Horizontal Row** (`WrapStyle: 2`) | Multi-line captions and text-wrapping are strictly prohibited. |
| **Vertical Position** | **Lower-Middle Third** (`MarginV: 520`, ~27% from bottom) | Safely clears platform seekbars/UI while staying below faces and chests. |
| **Horizontal Alignment**| Center (`Alignment: 2`) with `MarginL: 40, MarginR: 40` | Safe horizontal margins across all 9:16 devices. |
| **Minimum Display Time**| `0.60 s` | Short phrases (e.g. `"BioChroma."`, `"Ho detto:"`) remain readable. |
| **Gap Bridging** | Gaps < `0.22 s` bridged to 0s | Eliminates visual flicker between consecutive dialogue lines. |
| **Speech Tail Padding** | +`0.12 s` (keeping `0.08 s` breathing gap) | Follows natural vocal decay without cutting off end consonants. |
| **Audio Treatment** | **Bit-Exact Passthrough (`-c:a copy`)** | Never re-encode or compress original audio tracks. Zero A/V drift. |

---

## Verbatim Italian Script & Locked Terms

For BioChroma ads, captions must match the client's official verbatim Italian script with 100% precision:
1. **Locked Brand & Cosmetic Terms**:
   - `BioChroma`
   - `Centella Asiatica`
   - `Peptidi di Seta`
   - `Peptidi Dorati`
   - `skincare`, `retinolo`, `botox`, `filler`, `lifting`
2. **Accents & Apostrophes**:
   - Maintain exact Italian grave/acute accents (`è`, `é`, `à`, `ò`, `ù`, `ì`).
   - Maintain apostrophes (`l'ho`, `c'è`, `dov'è`, `cos'hai`, `un'amicizia`, `vent'anni`, `quell'agente`).
3. **Numbers**: Spelled out in full Italian words (e.g., *sessantatré*, *quarantotto*).
4. **Dialogue Punctuation & Quotes**:
   - Keep exact dialogue formatting: `Ho detto: “Ovvio, è fatta così.”`
5. **No Invented Text**: Delete captions during background noise, laughter, gasps, and pauses.

The complete canonical 103-chunk breakdown is stored in:
`references/biochroma_script.txt`

---

## Autonomous Execution

### Single-Command Automated Pipeline
Run the dedicated engine script from the repository root:

```powershell
.\.venv\Scripts\python.exe skills/biochroma-captions/scripts/generate_biochroma_captions.py
```

### CLI Parameters:
* `-i, --input <PATH>`: Source video file path (Optional: if omitted, automatically selects the latest `.mp4` inside `Input/`).
* `-o, --output <PATH>`: Destination path (Defaults to `Output/<video_basename>_captioned.mp4`).
* `--script-file <PATH>`: Custom script path if a variation is provided (Defaults to official BioChroma script).
* `--font-size <INT>`: Subtitle font size (Defaults to `78`).
* `--outline-width <FLOAT>`: Stroke width (Defaults to `4.0`).
* `--margin-v <INT>`: Vertical margin offset (Defaults to `520`).
* `--skip-render`: Generates `.ass` and `.srt` without video re-encoding for instant preview.

---

## Manual Step-by-Step Procedure

If running steps manually or customizing parts of the pipeline:

### Step 1: Transcribe Audio
Extract word-level timestamps using `faster-whisper` on CPU (int8):
```python
from faster_whisper import WhisperModel
model = WhisperModel("base", device="cpu", compute_type="int8")
segments, _ = model.transcribe("Input/<video>.mp4", word_timestamps=True, vad_filter=True)
```

### Step 2: Needleman-Wunsch Dynamic Programming Alignment
Align Whisper words against the verbatim BioChroma script chunks using the DP alignment engine to guarantee 100% textual accuracy while retaining exact spoken audio timestamps.

### Step 3: Build BioChroma ASS Header
```ini
[Script Info]
Title: BioChroma Italian Ad Subtitles
ScriptType: v4.00+
WrapStyle: 2
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Roboto,78,&H00FFFFFF,&H000000FF,&H00181818,&H00000000,-1,0,0,0,100,100,0.5,0,1,4.0,0,2,40,40,520,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:01.68,Default,,0,0,520,,Siamo entrati in casa
```

### Step 4: Render with NVENC Hardware Acceleration
Burn subtitles directly into the video stream while copying audio bit-for-bit:
```powershell
.\.venv\Scripts\ffmpeg.EXE -y -i "Input/<video>.mp4" -vf "subtitles=Output/<video>_subtitles.ass:fontsdir=fonts" -c:v h264_nvenc -preset p5 -cq 19 -b:v 0 -c:a copy "Output/<video>_captioned.mp4"
```
*(If NVENC is unavailable, fall back to `-c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p`)*.

---

## Deliverables Checklist
Every BioChroma captioning run must produce:
1. `Output/<name>_captioned.mp4`: Master captioned 4K / 9:16 video.
2. `Output/<name>_subtitles.ass`: Master ASS file with 78pt Roboto-Bold styling.
3. `Output/<name>_subtitles.srt`: Standard SRT file with matching timecodes.

