---
name: ugc-editor
description: >-
  UGC EDITOR - AI agent video editing skill for programmatic UGC and short-form video creation,
  cutting dead air, auto-captions, dynamic motion graphics, sound effects (SFX), and BGM mixing.
---

# UGC EDITOR

Comprehensive AI Agent Video Editing Skill designed for autonomous and programmatic production of high-converting, high-retention UGC (User-Generated Content), TikToks, Instagram Reels, and YouTube Shorts.

Compatible across AI agent environments: **Codex, Claude Code, Hermes Agent, Kliro CLI, Gemini CLI, and Antigravity**.

---

## Workspace I/O Rules (Input & Output Contract)

### 1. `Input/` (Source Footage)
- **Role**: Raw input repository manually uploaded/provided by the user.
- **Agent Behavior**:
  - The agent inspects `Input/` to find source videos (`.mp4`, `.mov`, `.mkv`, `.webm`, etc.).
  - **Multi-Clip Awareness**: When multiple raw clips are present (e.g. `clip 1.mp4`, `clip 2.mp4`, `clip 3.mp4`), the agent sequences them using natural numerical sorting before applying edits.
  - **Read-Only Rule**: Never overwrite, delete, or rename original files in `Input/`. All processing treats input files as immutable source assets.
  - If multiple files exist and none was specified, list available files in `Input/` and ask the user or process according to instruction.

### 2. `Output/` (Agent Rendered Results)
- **Role**: Destination directory for all AI agent edited videos and exports.
- **Agent Behavior**:
  - All rendered videos, cut segments, captioned exports, and final deliverables must be saved directly inside `Output/`.
  - **Standard Naming Conventions**:
    - `Output/<source_basename>_assembled.mp4`
    - `Output/<source_basename>_transitioned.mp4`
    - `Output/<source_basename>_trimmed.mp4`
    - `Output/<source_basename>_captioned.mp4`
    - `Output/<source_basename>_with_shape.mp4`
    - `Output/<source_basename>_with_sfx.mp4`
    - `Output/<source_basename>_zoomed.mp4`
    - `Output/<source_basename>_with_bgm.mp4`
    - `Output/<source_basename>_graded.mp4`
    - `Output/<source_basename>_master.mp4`
  - Clean up any temporary scratch files or store them in `Output/temp_scratch/` and delete upon render completion.

### 3. Supporting Assets
- `SFX/`: Curated library of 28 sound effects (whooshes, risers, hits, clicks, UI sounds, comedic audio).
- `BM/`: Background music tracks to be mixed into the edit.
- `.venv/`: Dedicated Python 3.11 virtual environment with FFmpeg 9.0+, FFprobe, MoviePy, Pydub, Scipy, Faster-Whisper, and media tools.

---

## Creative UGC Retention Framework

To maximize viewer watch time and engagement, video edits follow the **Hook → Value → CTA** framework:

1. **The First 3 Seconds (The Hook)**:
   - Immediate visual pattern interrupt: Punch zoom in (`1.15x`) with an upper-third `face` anchor.
   - First phrase emphasized with large kinetic typography and a bright pinpoint highlight (`STOP`, `NEVER`, `SECRET`).
   - Accompany the visual cut with a subtle `whoosh` or `riser` from `SFX/`.
2. **The Body (The Value / Retention Driver)**:
   - **No Hesitations**: Trim every pause longer than 0.4s down to 0.12s natural speech padding using `cut_dead_air.py`.
   - **Multi-Camera Illusion**: Alternate camera framing cuts (`1.0x` wide <-> `1.15x` punch) every 3 to 4 seconds using `apply_keyframes.py`.
   - **Contextual Visual Proof**: Whenever numbers, growth, or metrics are spoken, pop in an animated `bargraph` or `circular_motion` graphic using `apply_morphing_shapes.py`.
   - **Subtle Audio Micro-Rewards**: Place subtle UI clicks on key words using `add_sfx.py`.
   - **Dynamic Audio Bed**: Duck background music under dialogue so voice clarity is crisp, and swell music during scene transitions.
3. **The Call-to-Action (The Outro)**:
   - Punch zoom directly onto the speaker.
   - Pop a `rectangle` callout card with the next step ("FOLLOW FOR MORE", "LINK IN BIO").
   - Clean 1.5s audio fade-out.

---

## Universal Media Encoding Standards (Zero Playback Errors)

To guarantee that all produced videos play natively across Windows Media Player, macOS QuickTime, iOS, Android, web browsers, and social uploaders (TikTok, Instagram, YouTube) without decoding errors (e.g. `0x80004005: Unsupported encoding settings`), the following encoding rules are strictly enforced:

### 1. Mandatory Standard Pixel Format (`-pix_fmt yuv420p`)
* **Strict Rule**: Every FFmpeg command encoding video with `libx264` MUST explicitly include:
  ```bash
  -c:v libx264 -pix_fmt yuv420p -preset fast -crf 18
  ```
* **Why this is critical**: Complex filter operations (such as compositing transparent QuickTime RLE overlays in `apply_morphing_shapes.py`, `xfade` transitions in `apply_transitions.py`, or `colorbalance` in `color_grade.py`) default to `yuv444p` (`High 4:4:4 Predictive` profile). Consumer operating systems and mobile hardware decoders do NOT support 4:4:4 chroma subsampling. Omitting `-pix_fmt yuv420p` causes Windows Media Player and mobile devices to fail playback with error `0x80004005`.

### 2. Macroblock Dimension Alignment
* **Strict Rule**: Video dimensions must always be even integers:
  ```text
  w = trunc(target_w / 2) * 2
  h = trunc(target_h / 2) * 2
  ```
* Standard short-form UGC canvas is `1080x1920` (9:16 vertical).

### 3. Broadcast Audio Standardization
* **Strict Rule**: Always unify audio streams to AAC stereo at 48,000 Hz:
  ```bash
  -c:a aac -b:a 192k -ar 48000 -ac 2
  ```
  Prevents sample rate mismatch and audio/video sync drift during multi-clip stitching.

### 4. Windows Console UTF-8 Resilience
* **Strict Rule**: In all Python scripts executing in Windows PowerShell / Command Prompt, stdout and stderr must be reconfigured to UTF-8:
  ```python
  if sys.platform == "win32":
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
      sys.stderr.reconfigure(encoding="utf-8", errors="replace")
  ```
  Prevents `UnicodeEncodeError: 'charmap' codec can't encode character` when logging rich unicode or emoji characters.

---

## Complete Capabilities & Script Reference

### Capability 1: Dead Air & Silence Trimming (Jump-Cut Removal)

Automated dead air detection and trimming creates tight, dynamic, fast-paced UGC pacing (TikTok, Reels, Shorts) by removing silences, hesitations, and awkward pauses while keeping audio and video 100% in sync.

#### How It Works:
- Uses FFmpeg's `silencedetect` filter to capture exact microsecond silence markers.
- Inverts silence to active speech intervals with safety padding (`0.12s` default) so natural consonant plosives and breaths are never clipped.
- Executes single-pass stream trimming (`trim`, `atrim`, `setpts`, `asetpts`) and concatenation in FFmpeg to eliminate A/V sync drift.

#### How to Execute:
```powershell
.\.venv\Scripts\python.exe skills/ugc-editor/scripts/cut_dead_air.py -i "Input/<video_file>.mp4" -o "Output/<video_file>_trimmed.mp4"
```

#### CLI Parameters:
- `-i, --input <PATH>`: Source video path inside `Input/` (Required).
- `-o, --output <PATH>`: Destination path inside `Output/` (Defaults to `Output/<name>_trimmed.mp4`).
- `-n, --noise-db <FLOAT>`: Silence audio threshold in decibels (Default: `-32.0` dB). Lower values (e.g., `-38.0`) make cuts more conservative; higher values (e.g., `-28.0`) cut background room tone.
- `-s, --min-silence <FLOAT>`: Minimum pause length in seconds to trigger a cut (Default: `0.40`s).
- `-p, --padding <FLOAT>`: Safety buffer added to speech boundaries (Default: `0.12`s).

---

### Capability 2: Accurate Captions & Kinetic Text with Context PinPoint Emphasis

Generates word-level synchronized animated subtitles designed specifically for high-retention short-form videos (Hormozi / TikTok / Reels style).

#### Highlights:
1. **Accurate Word-Level Synchronization**: Powered by `faster-whisper`, providing microsecond timestamps for every spoken word.
2. **Short UGC Chunking**: Words are grouped into bite-sized 1–3 word phrases on screen to maintain high visual momentum.
3. **Kinetic Pop & Highlight**: The currently spoken word dynamically pops in scale (`115%` bounce) and switches to a bright highlight color while inactive words remain readable with high-contrast outlines and drop shadows.
4. **Context PinPoint Emphasis**:
   - High-impact context words (e.g. `MONEY`, `SECRET`, `STOP`, `RESULTS`, numbers `$100`, `3`, etc.) receive immediate emphasis.
   - PinPoint words scale larger (`125%` pop) and illuminate in a dedicated pinpoint accent color (e.g., Neon Green or Flame Red).
   - Custom pinpoint keywords can be supplied on the fly via `--pinpoints`.

#### How to Execute:
```powershell
.\.venv\Scripts\python.exe skills/ugc-editor/scripts/add_kinetic_captions.py -i "Output/<video_file>_trimmed.mp4" -o "Output/<video_file>_captioned.mp4" --style hormozi --pinpoints "secret,money,hack"
```

#### CLI Parameters:
- `-i, --input <PATH>`: Input video (from `Input/` or `Output/`) (Required).
- `-o, --output <PATH>`: Destination video path (Defaults to `Output/<name>_captioned.mp4`).
- `-p, --pinpoints <STR>`: Comma-separated context emphasis keywords (e.g., `--pinpoints "ai,freedom,proven,secret"`).
- `-s, --style <STR>`: Visual theme:
  - `hormozi`: Bright yellow active highlight, neon green pinpoint emphasis, thick black stroke.
  - `neon_green`: Neon green active highlight, electric yellow pinpoint emphasis.
  - `clean_white`: Crisp white typography with hot red/yellow pinpoint pop.
- `-w, --max-words <INT>`: Max words per subtitle line (Default: `3`).
- `-m, --model <STR>`: Whisper model size: `tiny`, `base` (default), or `small`.
- `--burn / --no-burn`: Whether to burn subtitles directly into the video stream (Default: `--burn`).

---

### Capability 3: Dynamic Morphing Shapes & Visual Engagement Graphics

Applies animated motion graphic overlays (bar graphs, circular progress motions, morphing rounded rectangles, focus target rings, viral badge callouts, and retention progress bars) to maximize viewer engagement during key explanations or data claims.

#### Available Shapes:
- **`bargraph`**: Rising multi-bar growth chart with kinetic ease-out bounce, glassmorphism container, and metric header (ideal for growth, revenue, comparison claims).
- **`circular_motion`**: Dynamic 360° circular progress ring with radial arc draw, center metric readout (e.g. `98%`, `10x`), and expanding radar pulses.
- **`rectangle`**: Morphing pop-in callout badge card with glowing border and accent pill (ideal for tips, warnings, alerts, step labels).
- **`focus_ring`**: Pulsating circular reticle with target crosshairs to draw the viewer's eye to a product or on-screen detail.
- **`badge_callout`**: Attention-grabbing pill badge with glowing double border and icon pop (ideal for `🔥 GAME CHANGER`, `🚀 10X LEAP`, `⚠️ WARNING`, `💡 SECRET HACK`).
- **`progress_bar`**: Sleek animated retention progress bar moving along the bottom of the video with glowing tip to prevent drop-off.

#### How to Execute:
```powershell
.\.venv\Scripts\python.exe skills/ugc-editor/scripts/apply_morphing_shapes.py -i "Output/<video_file>.mp4" -o "Output/<video_file>_with_shape.mp4" --shape bargraph --start 2.5 --duration 3.0 --label "+350% GROWTH" --color cyan --position center
```

#### CLI Parameters:
- `-i, --input <PATH>`: Source video path (Required).
- `-o, --output <PATH>`: Output video path.
- `-s, --shape <STR>`: Shape type (`bargraph`, `circular_motion`, `rectangle`, `focus_ring`, `badge_callout`, `progress_bar`).
- `-t, --start <FLOAT>`: Timestamp in seconds when shape animation begins (e.g. `2.5`).
- `-d, --duration <FLOAT>`: How many seconds the graphic stays active (Default: `3.0`s).
- `-l, --label <STR>`: Text label, statistic, or message inside the shape graphic.
- `-c, --color <STR>`: Color palette: `cyan`, `yellow`, `green`, `orange`, `purple`.
- `-pos, --position <STR>`: Screen position: `center`, `top_center`, `bottom_center`.

---

### Capability 4: Context SFX Layering & Precision Transient Auto-Sync

Intelligently layers and mixes sound effects from the curated `SFX/` library to punctuate cuts, transitions, pinpoint word reveals, and morphing shapes with frame-accurate timing.

#### Transient Peak Alignment Engine:
- **Automatic Silence Stripping**: Automatically detects and trims dead air and leading silence from raw audio assets (e.g. eliminating the 3.5s silent pre-roll in `SLAP SFX.mp3`).
- **Acoustic Crest / Transient Alignment**: Analyzes the audio waveform to identify the exact millisecond of the sound's peak volume/impact. Offsets audio start (`t_target - t_peak`) so the physical punch of the sound (shutter snap, slap impact, UI chime, whoosh crescendo) hits on the exact frame of the visual event.

#### Available SFX Categories (28 Assets):
- **`whoosh`**: Swipes, transitions, shape animations, slide-ins (`whoosh-6316.mp3`, `WHOOSH 2 SFX.mp3`, `WHOOSH 6 SFX.mp3`, `Whoosh Fast.wav`).
- **`click`**: Pinpoint pop-ins, kinetic text events, camera clicks (`Camera Shutter`, `Switch Click.mp3`, `UI Beep 5.wav`, `Typewriter 2.wav`).
- **`riser`**: Suspense hooks, dramatic builds, questions (`Sharp Riser.wav`, `Suspense SFX.mp3`, `Riser Short.wav`).
- **`impact`**: Dramatic reveals, punchlines, scene shifts (`SLAP SFX.mp3`, `Power Up.mp3`, `Scene Change.mp3`, `Splash.mp3`).
- **`funny`**: Mistakes, disbelief, sarcastic comedic reactions (`Nope.mp3`, `Quack SFX.mp3`, `Sad Violin.mp3`, `Quick Fart SFX.mp3`, `Toy duck.mp3`).

#### How to Execute:
1. **List all available SFX**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/add_sfx.py list
   ```
2. **Apply SFX via cues**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/add_sfx.py apply -i "Output/<video_file>.mp4" -o "Output/<video_file>_with_sfx.mp4" --cues "1.5:whoosh, 3.2:click, 5.0:slap" --volume 0.35
   ```
3. **Auto-Sync to Subtitle Pinpoints**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/add_sfx.py apply -i "Output/<video_file>.mp4" -o "Output/<video_file>_with_sfx.mp4" --from-ass "Output/<video_file>_captions.ass" --volume 0.30
   ```

#### CLI Parameters:
- `-i, --input <PATH>`: Input video path (Required).
- `-o, --output <PATH>`: Output video path.
- `-c, --cues <STR>`: Timestamped sound cues (e.g. `'1.5:whoosh, 3.0:ui_click, 6.2:impact'`).
- `--from-ass <PATH>`: Path to `.ass` subtitle file to auto-sync subtle clicks on pinpoint words.
- `-v, --volume <FLOAT>`: Relative volume (Default: `0.35` / ~-9dB attenuation so speech stays clear).

---

### Capability 5: Keyframed Camera Zooms & Dynamic Reframing (Smart Zooming)

Applies continuous slow zooms, punch-cut reframing, and dialogue-aware smart camera switches to simulate high-end multi-camera production.

#### Available Modes:
- **`smart_cuts`** *(UGC Standard)*: Dialogue- and scene-aware camera switching. Instead of arbitrary modulo timers, camera angle changes occur strictly on **clip transitions or sentence pauses**:
  - **The Hook (0.0s - 2.0s)**: Opens with an immediate close-up punch (`1.18x`) to capture eye contact, then resets to wide (`1.0x`) as the premise is laid out.
  - **Hero Reveal / Discovery**: Punches in (`1.18x`) to highlight the solution/product.
  - **Demonstration**: Resets to wide/medium (`1.05x`) giving visual space for hands and actions.
  - **Call-to-Action**: Punches in (`1.18x`) for commanding final authority.
- **`slow_push`**: Gradual continuous zoom-in (`1.0x -> 1.15x`) that builds emotional connection and focus during core explanations.
- **`slow_pull`**: Continuous pull-back (`1.15x -> 1.0x`) for opening hooks or section summaries.
- **`punch_cuts`**: Alternates between wide (`1.0x`) and punch-zoom (`1.15x`) every N seconds (e.g. every `3.5s`).
- **`custom`**: Explicit keyframe cues (`--cues "0:1.0, 3.5:1.18, 7.0:1.0"`).

#### Smart Talking-Head Anchor (`--anchor face`):
Standard zoom filters crop toward the center (cutting off hair/foreheads and framing chests). The `face` anchor offsets the vertical crop to the upper-third (`0.35` factor) so the speaker's eyes and face remain centered and flattering.

#### How to Execute:
```powershell
.\.venv\Scripts\python.exe skills/ugc-editor/scripts/apply_keyframes.py -i "Output/<video_file>.mp4" -o "Output/<video_file>_zoomed.mp4" --mode smart_cuts --max-zoom 1.18 --anchor face --scene-cuts "7.7,10.9,16.9"
```

#### CLI Parameters:
- `-i, --input <PATH>`: Source video path (Required).
- `-o, --output <PATH>`: Output video path.
- `-m, --mode <STR>`: Zoom profile (`smart_cuts`, `slow_push`, `slow_pull`, `punch_cuts`, `custom`).
- `-z, --max-zoom <FLOAT>`: Peak zoom factor (Default: `1.18`x / 118%).
- `-a, --anchor <STR>`: Framing anchor (`face`, `center`, `top`, `bottom`).
- `--scene-cuts <STR>`: Comma-separated scene cut timestamps (e.g. `'7.76, 10.97, 16.97'`).
- `--from-ass <PATH>`: Subtitle `.ass` file to align zooms to dialogue phrases.
- `-a, --anchor <STR>`: Focus anchor: `face` (default for talking heads), `center`, `top`, `bottom`.
- `-c, --cycle <FLOAT>`: Cycle period in seconds for `punch_cuts` (Default: `3.5`s).
- `--cues <STR>`: Custom keyframe cues (e.g. `'0:1.0, 4.0:1.18, 8.0:1.0'`).

---

### Capability 6: Aesthetic Color Grading (User-Driven Looks & Presets)

Provides instantaneous aesthetic stylization matching user creative direction, transforming flat phone footage into punchy, high-converting video.

#### Curated Aesthetic Presets:
- **`vibrant_pop`** *(Default UGC standard)*: Boosted saturation (`+28%`), crisp contrast, warm skin tones, and rich highlights.
- **`warm_golden`**: Golden hour glow, warm amber midtones, flattering skin, and soft vignette.
- **`teal_and_orange`**: Blockbuster cinematic split-toning (cool shadows, amber highlights).
- **`clean_bright`**: High-key commercial studio aesthetic, crisp true whites, natural skin.
- **`moody_dark`**: Modern tech / luxury dark look with cool highlights and deep rich blacks.
- **`retro_film`**: 90s vintage film aesthetic with lifted faded blacks, amber tints, and vignette.
- **`bw_noir`**: High-contrast dramatic black and white.

#### How to Execute:
1. **List all presets**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/color_grade.py list
   ```
2. **Apply a curated preset**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/color_grade.py apply -i "Output/<video_file>.mp4" -o "Output/<video_file>_graded.mp4" --preset vibrant_pop
   ```
3. **Fine-tune with custom adjustments**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/color_grade.py apply -i "Output/<video_file>.mp4" -o "Output/<video_file>_graded.mp4" --preset warm_golden --temp 0.2 --vignette 0.25
   ```

#### CLI Parameters:
- `-i, --input <PATH>`: Source video path (Required).
- `-o, --output <PATH>`: Output video path.
- `-p, --preset <STR>`: Desired aesthetic (`vibrant_pop`, `warm_golden`, `teal_and_orange`, `clean_bright`, `moody_dark`, `retro_film`, `bw_noir`).
- `-b, --brightness <FLOAT>`: Brightness shift (`-0.5` to `0.5`, default `0.0`).
- `-c, --contrast <FLOAT>`: Contrast multiplier (`0.5` to `2.0`, default `1.0`).
- `-s, --saturation <FLOAT>`: Saturation multiplier (`0.0` to `2.5`, default `1.0`).
- `-t, --temp <FLOAT>`: Color temperature (`-1.0` cool to `1.0` warm).
- `-v, --vignette <FLOAT>`: Optical edge darkening (`0.0` to `1.0`).
- `--lut <PATH>`: Path to custom `.cube` 3D LUT file.

---

### Capability 7: Multi-Clip Assembly & Natural Sequence Stitcher

Detects multiple video clips uploaded into `Input/` (e.g. `clip 1.mp4`, `clip 2.mp4`, `clip 3.mp4`, `clip 10.mp4`, `take_1.mp4`), sorts them naturally, normalizes formats, and stitches them into a unified master video.

#### Highlights:
1. **Natural Number Sorting**: Handles real human naming patterns like `clip 1`, `clip 2`, ... `clip 10` so that `clip 10` is placed after `clip 9` (preventing standard alphabetical sorting bugs where `10` comes before `2`).
2. **Multi-Source Format Normalization**: Automatically unifies differing smartphone resolutions, variable frame rates (standardizes to 30 fps), and mixed audio streams (48kHz stereo) into a clean vertical canvas (`1080x1920`) without black bar distortion.
3. **Missing Audio Handling**: Automatically synthesizes silent audio buffers if any B-roll clip lacks an audio track, preventing concatenation stream dropouts.

#### How to Execute:
1. **List all clips in natural sequence**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/stitch_clips.py list -i Input/
   ```
2. **Assemble all clips in natural order**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/stitch_clips.py stitch -i Input/ -o Output/assembled_sequence.mp4 --res 1080x1920 --fit crop
   ```
3. **Stitch with custom filename order**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/stitch_clips.py stitch -i Input/ -o Output/assembled_sequence.mp4 --order "hook.mp4,body.mp4,cta.mp4"
   ```

#### CLI Parameters:
- `-i, --input-dir <PATH>`: Directory containing raw source clips (Default: `Input/`).
- `-o, --output <PATH>`: Target output path (Default: `Output/assembled_sequence.mp4`).
- `-p, --pattern <STR>`: Glob pattern filter (e.g. `clip*.mp4`).
- `--order <STR>`: Explicit comma-separated order of filenames.
- `-r, --res <STR>`: Target resolution (`1080x1920` vertical default or `auto`).
- `--fps <INT>`: Output frame rate (Default: `30` fps).
- `--fit <STR>`: Fit strategy: `crop` (fills full screen, UGC standard) or `pad` (letterbox).

---

### Capability 8: Engaging Visual Transitions with Auto-Synced Whoosh SFX

Stitches multiple raw clips in `Input/` using dynamic visual transitions (swipes, snap zooms, iris reveals, and flashes) while automatically syncing punchy whoosh SFX at every transition cut.

#### Supported Transitions:
- **`slide_left` / `slide_right`**: Fast horizontal swipe (signature TikTok/Reels feed swipe).
- **`slide_up`**: Vertical card scroll transition.
- **`smooth_left`**: Eased directional motion blur wipe.
- **`zoom_in`**: High-energy snap zoom punch into the next scene.
- **`circle_crop`**: Retro circular iris reveal (focuses viewer attention on the subject center).
- **`fade_white`**: High-energy flash-to-white scene transition.
- **`fade_black`**: Theatrical dip-to-black.
- **`pixelize`**: Digital pixel glitch wipe (ideal for gaming/tech).
- **`random`**: Alternates engaging transitions dynamically across every cut point.

#### Auto-Synced Whoosh SFX & Anti-Mumble Crossfading:
1. **Snappy UGC Duration (`0.22s`)**: Transitions are configured to `0.22s` by default, fitting completely within natural speech pause buffers (`0.24s`) without cutting off spoken consonants.
2. **Exponential Dialogue Crossfade**: Uses `acrossfade=d=0.22:curve1=exp:curve2=exp` so that dialogue across consecutive clips transitions cleanly without speech overlap or vocal mumbling.
3. **Transient Peak Whoosh Alignment**: Selects punchy, low-latency whooshes (`whoosh-6316.mp3`, `WHOOSH 2 SFX.mp3`) and aligns their acoustic peak directly to the midpoint of the transition wipe for maximum impact.

#### How to Execute:
1. **List all transitions**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/apply_transitions.py list
   ```
2. **Apply transitions with auto-whoosh SFX**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/apply_transitions.py apply -i Input/ -o Output/transitioned_sequence.mp4 --transition slide_left --duration 0.22 --auto-sfx
   ```
3. **Randomized dynamic transitions**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/apply_transitions.py apply -i Input/ -o Output/transitioned_sequence.mp4 --transition random --duration 0.22
   ```

#### CLI Parameters:
- `-i, --input-dir <PATH>`: Directory containing source clips (Default: `Input/`).
- `-o, --output <PATH>`: Target output video path.
- `-t, --transition <STR>`: Transition style (`slide_left`, `slide_up`, `smooth_left`, `zoom_in`, `circle_crop`, `fade_white`, `pixelize`, `random`).
- `-d, --duration <FLOAT>`: Transition length in seconds (Default: `0.22`s).
- `--auto-sfx / --no-sfx`: Whether to auto-sync whoosh audio effects (Default: `--auto-sfx`).
- `-r, --res <STR>`: Output canvas resolution (Default: `1080x1920`).
- `--fps <INT>`: Unified frame rate (Default: `30` fps).

---

### Capability 9: Background Music (BGM) with Intelligent Voice-Ducking

Mixes background music tracks from `BM/` behind video audio using broadcast **sidechain compression** (`sidechaincompress`):
- When the creator speaks, background music automatically attenuates smoothly by a **5:1 ratio**.
- During pauses and visual transitions, background music swells back up seamlessly to maintain audio rhythm.
- Automatically fades out over `1.5s` at the exact end of the video.

#### How to Execute:
1. **List all tracks in BM/**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/add_bgm.py list
   ```
2. **Mix BGM with automatic sidechain voice-ducking**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/add_bgm.py mix -i Output/<video_file>.mp4 -o Output/<video_file>_with_bgm.mp4 --volume 0.18 --ducking 5.0
   ```

#### CLI Parameters:
- `-i, --input <PATH>`: Input video path (Required).
- `-o, --output <PATH>`: Output video path.
- `-m, --music <PATH/NAME>`: Specific music track filename or search query from `BM/`.
- `-v, --volume <FLOAT>`: Base music volume (Default: `0.18`).
- `-d, --ducking <FLOAT>`: Sidechain compression ratio (Default: `5.0`).
- `--fade-out <FLOAT>`: End-of-video fade duration (Default: `1.5`s).

---

### Capability 10: The Autonomous UGC Creative Director Pipeline

Orchestrates all editing capabilities into an end-to-end autonomous pipeline, allowing AI agents to generate a production-ready viral UGC video in one high-level execution:

```powershell
.\.venv\Scripts\python.exe skills/ugc-editor/scripts/ugc_director.py produce -i Input/ -o Output/viral_master.mp4 --preset viral_hook
```

#### Available Creative Presets:
- **`viral_hook`** *(Default UGC standard)*: Fast-paced jump cuts, alternating punch-cut zooms, vibrant commercial color grade, whooshes, and high-contrast yellow/green Hormozi captions.
- **`storyteller`**: Narrative cinematic look, warm golden hour grade, continuous slow push zoom, subtle risers, and clean white captions.
- **`saas_explainer`**: Modern tech product look, dark luxury grade, animated bar graphs/circular progress rings, and neon green/cyan accents.

#### CLI Parameters:
- `-i, --input <PATH>`: Directory or video file in `Input/` (Default: `Input`).
- `-o, --output <PATH>`: Final output path in `Output/`.
- `-p, --preset <STR>`: Creative preset (`viral_hook`, `storyteller`, `saas_explainer`).
- `--trim / --no-trim`: Automatically cut dead air (Default: `--trim`).
- `--captions / --no-captions`: Burn kinetic captions (Default: `--captions`).
- `--zooms / --no-zooms`: Apply dynamic camera reframing (Default: `--zooms`).
- `--sfx / --no-sfx`: Layer sound effects (Default: `--sfx`).
- `--bgm / --no-bgm`: Mix background music with voice ducking (Default: `--bgm`).
- `--grade / --no-grade`: Apply aesthetic color grading (Default: `--grade`).
- `--normalize-loudness / --no-normalize-loudness`: Broadcast -14 LUFS loudness normalization (Default: `--normalize-loudness`).
- `--pinpoints <STR>`: Custom context keywords for caption scaling emphasis.

---

### Capability 11: Auto-Beat Detection & Visual Waveform Analysis

Extracts musical rhythm transients using a 4th-order Butterworth bandpass filter (45–180Hz) and sliding window peak picking:
- **Beat 1 (Downbeat Kicks)**: Primary yellow diamond markers for cutting between main scenes.
- **Beat 2 (Sub-rhythms / 8th notes)**: Cyan micro-markers for rapid jump cuts and b-roll inserts.
- **BPM Tempo Estimation & 120-slice Waveform Envelope**.

```powershell
.\.venv\Scripts\python.exe skills/ugc-editor/scripts/detect_beats.py analyze -i "BM/Upbeat Viral Pop.mp3"
```

---

### Capability 12: Speed Ramping Curves (Montage, Bullet Time, Flash In, Hero)

Applies variable velocity speed ramping with dynamic PTS mapping and chained `atempo` audio time-stretching:
- **`montage`**: Fast intro (2.5x), slow dip (0.6x), explosive acceleration (2.8x), rhythmic finish.
- **`bullet_time`**: Matrix freeze: fast entry (3.0x), ultra-slow-mo pocket (0.2x), high-speed exit.
- **`flash_in`**: 4.0x plunge into standard playback.
- **`flash_out`**: Acceleration into transition cut (1.0x -> 4.5x).
- **`hero`**: Slow cinematic build (0.6x) into peak impact (3.5x).
- **`custom`**: Arbitrary Bezier curve points `[(time_pct, speed), ...]`.
- **`--smooth-slowmo`**: Optical flow motion interpolation (`minterpolate`) for 60fps slow motion.

```powershell
.\.venv\Scripts\python.exe skills/ugc-editor/scripts/apply_speed_ramp.py apply -i "Input/1.mp4" -o "Output/ramped.mp4" -p bullet_time
```

---

### Capability 13: Automatic Loudness Normalization (-14 LUFS EBU R128)

Analyzes and normalizes audio to TikTok, Instagram Reels, and YouTube broadcast standards:
- **EBU R128 / ITU-R BS.1770-4 2-Pass Loudness Control**: Targets integrated loudness of `-14.0 LUFS` with True Peak bounded at `-1.5 dBTP` to prevent inter-sample clipping on mobile speakers.
- **Diagnostic Measurement**:
```powershell
.\.venv\Scripts\python.exe skills/ugc-editor/scripts/normalize_loudness.py measure -i "Output/viral_master.mp4"
```
- **Precision Normalization**:
```powershell
.\.venv\Scripts\python.exe skills/ugc-editor/scripts/normalize_loudness.py normalize -i "Output/viral_master.mp4" -o "Output/master_normalized.mp4" -t -14.0
```

---

### Capability 14: Geometric Masking & Feather Slider

Applies customizable geometric masks with adjustable Gaussian feather softness, rotation, corner roundness, and invert controls:
- **`circle`**: Spotlight circle/oval cutout for faces, products, or PIP bubbles.
- **`rectangle`**: Rounded rectangular window with customizable corner radius.
- **`split`**: Before/after comparison split line with adjustable angle and position.
- **`filmstrip`**: Dual cinematic letterboxing bars.
- **`heart` & `star`**: Stylized aesthetic shapes.
- **`feather`**: 0px to 100px Gaussian blur radius for seamless dissolved edge transitions.
- **`invert`**: Flips mask to reveal the outer region instead of inner.

```powershell
.\.venv\Scripts\python.exe skills/ugc-editor/scripts/apply_mask.py apply -i "Input/1.mp4" -o "Output/masked.mp4" -s circle -f 24.0 --width 0.70 --height 0.70
```

---

### Capability 15: Motion Tracking & Face Following

Tracks face and object motion frame-by-frame using OpenCV TrackerMIL and optical flow, generates smooth camera reframing coordinates, and binds subtitles or stickers to follow the moving subject:
- **`track`**: Analyzes bounding box trajectories `(t, x, y, w, h)` across video frames with exponential moving average jitter smoothing.
- **`reframe`**: Dynamically crops and pans the camera at adjustable zoom levels (1.1x–1.5x) keeping the face locked inside the TikTok/Reels upper-third safe zone.
- **`pin_text`**: Binds kinetic subtitles or stickers to track subject motion in real-time.
- **Axis Locking**: Options for `both`, horizontal `x` only, or vertical `y` only pan locks.

#### CLI Execution:
1. **Analyze Trajectory**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/track_motion.py track -i "Input/1.mp4" -o "Output/tracking_1.json" -t face -s 0.75
   ```
2. **Apply Dynamic Camera Reframe**:
   ```powershell
   .\.venv\Scripts\python.exe skills/ugc-editor/scripts/track_motion.py reframe -i "Input/1.mp4" -o "Output/reframed_1.mp4" -t "Output/tracking_1.json" -z 1.25 -a face --axis both
   ```

---

### Capability 16: Chroma Key & Smart Cutout (Green Screen / Background Remover)

Removes green screen, blue screen, or custom color backdrops, with anti-aliasing smoothness, shadow retention, color spill suppression, and background compositing:
- **`chroma`**: Keys out color with customizable Similarity (0–100%) and Smoothness (0–100% soft edge anti-aliasing).
- **`sample_color`**: Eyedropper sampling tool that reads exact hex color from video frames.
- **`despill`**: Eliminates green/blue fringe reflections on subject hair, skin, and shoulders (`despill=type=green:mix=0.5`).
- **`smart_cutout`**: Portrait cutout with optional neon glow or solid stroke outline.
- **Composited Backdrops**:
  - `blur`: Cinematic UGC style — splits the stream, applies 25px Gaussian boxblur to background, and overlays crisp keyed foreground.
  - `color`: Replaces backdrop with clean studio color (e.g. `#18181C`).
  - `transparent`: Output with alpha channel or dark canvas.

#### CLI Execution:
```powershell
.\.venv\Scripts\python.exe skills/ugc-editor/scripts/apply_cutout.py chroma -i "Input/1.mp4" -o "Output/cutout_1.mp4" -c "#00FF00" -s 30 -m 15 -w 20 -b blur
```


