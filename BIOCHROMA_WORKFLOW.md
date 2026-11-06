# BioChroma Ad Reskinning & Localization Workflow
## End-to-End Operating Procedure for AI Video Editors

This document outlines the complete workflow for taking a winning competitor video ad, reskinning it for **Client BioChroma**, aligning it with a translated Italian voiceover, managing pacing gaps and competitor product removals, and producing client-ready deliverables.

---

## 1. Executive Summary & Core Concept

### What is a "Creative Reskin"?
A creative reskin takes a proven winning ad structure from a competitor (e.g. English US beauty ad) and adapts it for BioChroma in the Italian market:
* **Same narrative beats**: The soap-opera drama hook (jealousy, real estate agent, secret serum, Korean silk peptides).
* **Brand swap**: Competitor product name and packaging are replaced with **BioChroma**.
* **New audio**: A native Italian voiceover (`.mp3`) replaces the competitor's audio track.
* **Retained footage**: High-converting competitor lifestyle scenes (walking into the house, husband glancing, facial reactions, stairs) are retained.
* **Replaced footage**: Competitor product bottles, logos, and pacing timing gaps are replaced with **AI Video (Runway / Kling / Luma)** or **BioChroma 3D bottle inserts**.

---

## 2. The 3 Editing Challenges & How We Solve Them

| Challenge | Why It Happens | The Solution |
| :--- | :--- | :--- |
| **Language Barrier** | You don't speak Italian, making it difficult to match visuals to spoken lines. | **Bilingual Storyboard Map**: Automatically transcribes Italian and provides side-by-side English translations with exact timecodes and visual directions. |
| **Pacing & Timing Mismatch** | Italian sentence structure and syllable counts are often longer than the original competitor language. | **Audio-First Timeline Slicing**: The Italian voiceover is the master clock. Competitor clips and placeholder cards are trimmed to the exact microsecond duration of each Italian dialogue cue. |
| **Competitor Product Shots** | Competitor bottles/droppers must be removed. | **Packaging Removal**: Cuts competitor bottles and replaces with BioChroma bottle placeholder. |
| **Texture & Application Mismatch** | Competitor ads often feature thick creams, tubs, peel-off masks, or Quasi-Collagen film, whereas **BioChroma is a translucent liquid serum with light gold silk threads**. | **Texture Cut & Regeneration**: Automatically flags and cuts incompatible cream/mask applications, inserting a dedicated Texture Placeholder with Kling/Runway prompts for liquid gold serum. |

---

## 3. Product Specification: BioChroma Texture vs. Incompatible Formats

| Product Format | Competitor Reference Visual | BioChroma Standard (What Must Appear) | Action Required |
| :--- | :--- | :--- | :--- |
| **Formula / Texture** | Thick white cream, moisturizer tub, pink paste, Quasi-Collagen film, peel-off mask. | **Translucent liquid serum with micro-fine suspended golden silk threads**. | **CUT OUT** and replace with `PLACEHOLDER_texture_gold_serum`. |
| **Dispenser** | Tub jar scoop, pump bottle, sheet packet. | **Glass dropper pipette** dispensing clear liquid with shimmering gold threads. | **CUT OUT** and replace with `PLACEHOLDER_dropper_application`. |
| **Skin Application** | Peeling off rubber mask, slathering heavy white opaque cream on cheeks. | **Gentle upward lifting massage** of dewy, clear liquid serum absorbing cleanly into skin. | **CUT OUT** and replace with `PLACEHOLDER_dewy_absorption`. |

---

## 4. The Numbered Sequence Folder Architecture

To allow complete manual editing in **CapCut**, **Premiere Pro**, or **DaVinci Resolve**, the engine organizes the project into a sequential numbered workspace:

```text
📁 Output/biochroma_reskin_01/
│
├── 📄 STORYBOARD_GUIDE.md             <-- Bilingual Cheat Sheet (Italian + English + Prompts)
├── 🎵 00_master_voiceover.mp3         <-- Clean Italian voiceover (Master audio)
├── 📝 subtitles_78pt_roboto.ass       <-- Client BioChroma ASS subtitles (78pt, MarginV 520)
├── 📝 subtitles.srt                   <-- Standard SRT subtitles
├── 🎬 rough_cut_preview.mp4           <-- Full preview video (Footage + Placeholders + VO + Subs)
│
└── 📁 clips/                           <-- Individual numbered clips (in chronological order)
    ├── 01_00.00-01.68_KEEP_house_entry.mp4
    ├── 02_01.68-03.45_KEEP_husband_glance.mp4
    ├── 03_03.45-06.20_PLACEHOLDER_ai_broll.mp4         <-- Visual Gap (Computed from Italian VO: 2.75s)
    ├── 04_06.20-08.10_KEEP_woman_reaction.mp4
    ├── 05_08.10-12.40_PLACEHOLDER_product_bottle.mp4   <-- Competitor Cut (Computed from Italian VO: 4.30s)
    ├── 06_12.40-15.00_KEEP_walking_downstairs.mp4
    └── ...
```

### Why This Architecture Eliminates Hassle:
1. **Zero Guesswork Timeline Import**: Select all files in `clips/` and drag them into CapCut / Premiere. They snap onto the timeline in **exact chronological sequence** (`01`, `02`, `03`...).
2. **100% Dynamic Durations (NO Hardcoded Defaults)**:
   * The duration of every placeholder and clip is **never fixed or defaulted**.
   * It is dynamically calculated from the exact millisecond timestamps of the Italian `.mp3` voiceover.
   * If the Italian actress speaks a line for `1.42s`, the placeholder is generated for exactly `1.42s` (43 frames). If she takes `4.85s`, the placeholder is generated for exactly `4.85s` (146 frames).
3. **Perfect Audio Synchronization**: Every clip in the folder is pre-cut to match the exact duration of the Italian voiceover segment beneath it. The playhead never drifts out of sync.
4. **Non-Destructive Manual Editing**: You can freely swap out placeholder clips with newly generated AI clips right in your NLE, or simply replace the file in the folder and re-render.

---

## 5. The Bilingual Storyboard Cheat Sheet (`STORYBOARD_GUIDE.md`)

This markdown guide acts as the editor's translation bridge and AI prompt sheet:

| Clip # | Timecode | Duration | Status | Italian Spoken | English Translation | Visual Action Needed | Kling / Runway AI Prompt |
| :---: | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| `01` | `00:00 - 01.68` | 1.68s | `KEEP` | *"Siamo entrati in casa"* | *"We walked into the house"* | Competitor Shot 1 (couple entering) | — |
| `02` | `01.68 - 03.45` | 1.77s | `KEEP` | *"e i suoi occhi sono andati dritti a lei"* | *"and his eyes went straight to her"* | Competitor Shot 2 (husband looking) | — |
| `03` | `03.45 - 06.20` | 2.75s | `REPLACE (GAP)` | *"Lo stesso sguardo che aveva per me quando avevo la metà dei miei anni."* | *"The same look he had for me when I was half my age."* | **Visual Gap**: Pacing deficit in competitor footage. | `Cinematic close-up of a 45-year-old elegant Italian woman looking at her husband with subtle sadness and jealousy, dramatic natural window lighting, 4k.` |
| `04` | `06.20 - 08.10` | 1.90s | `KEEP` | *"L’ho odiata a prima vista."* | *"I hated her at first sight."* | Competitor Shot 3 (subtle facial smirk/reaction) | — |
| `05` | `08.10 - 12.40` | 4.30s | `REPLACE (PRODUCT)` | *"Una piccola fiala con dei fili dorati che spuntava dalla borsa..."* | *"A small vial with golden threads poking out of the bag..."* | **Competitor Product Removed**: Replace with BioChroma packaging. | `Macro 4k commercial close-up of a luxury cosmetic vial labeled 'BioChroma' containing shimmering golden silk threads peeking out of a designer leather handbag, shallow depth of field.` |
| `06` | `12.40 - 15.80` | 3.40s | `REPLACE (TEXTURE)` | *"L’ho messa quella sera e ho sentito subito un tiraggio..."* | *"I put it on that evening and felt an immediate lift..."* | **Texture Mismatch Cut**: Competitor shows thick cream or collagen mask. Must be liquid gold serum. | `Commercial macro close-up of glass dropper dispensing a single drop of translucent liquid serum with micro-fine suspended golden silk threads onto high cheekbone, dewy glass skin, soft upward lifting massage, warm bathroom lighting, 4k 60fps.` |

---

## 6. The Static Visual Placeholder Slate Design

Every placeholder clip (`.mp4` / `.png`) is generated on a dark editorial canvas (1080×1920) containing:
1. **Type Tag**:
   * `[⚠️ COMPETITOR PRODUCT CUT - REPLACE WITH BIOCHROMA]` (Red/Gold Accent)
   * `[⚠️ TEXTURE MISMATCH CUT - REPLACE WITH GOLD SERUM]` (Gold/Amber Accent)
   * `[🎬 VISUAL TIMING GAP - REGENERATE WITH AI VIDEO]` (Cyan/Blue Accent)
2. **Exact Required Duration**: e.g., `Duration: 3.20s (96 frames @ 30fps)`.
3. **Audio Context**: Spoken Italian line + English translation.
4. **Visual Direction & AI Prompt**: Recommended prompt to copy/paste directly into **Kling**, **Runway Gen-3**, or **Luma Dream Machine**.

---

## 7. Frame-Accurate Cut Protocol & 4-Frame Visual Review Strip

To guarantee 100% surgical accuracy so that **not even a single frame of the competitor product or incompatible cream/mask leaks through**, the workflow enforces frame-accurate cutting:

### 1. Millisecond & Frame Precision (1/30th s)
* **Scene Cut Snapping**: The tool uses FFmpeg scene detection (`gt(scene, 0.25)`) to identify exact camera cuts. When the competitor product is a dedicated B-roll shot, the cut snaps cleanly to the camera transition.
* **Intra-Shot Frame Scan**: When the product appears mid-shot (e.g. pulled from a handbag), the engine scans frame-by-frame at 30fps to isolate the exact `Start Frame` and `End Frame`.

### 2. The 4-Frame Visual Review Strip
Before finalizing cuts, the tool exports a 4-image visual review strip into `preview_frames/cuts_review/`:
* `cut_01_frame_511_BEFORE.jpg`: Last safe frame before competitor product appears.
* `cut_01_frame_512_START.jpg`: First frame where competitor product is visible (Cut starts).
* `cut_01_frame_604_END.jpg`: Last frame where competitor product is visible (Cut ends).
* `cut_01_frame_605_AFTER.jpg`: First safe frame after competitor product exits.

You can open and verify these 4 photos with your own eyes in seconds to confirm that zero competitor product remains.

### 3. Exact Re-Encoding (No Keyframe Drift)
To avoid keyframe (GOP) quantization errors where standard players bleed 0.5s of trimmed footage, all slices are processed with exact frame selection:
```bash
-vf "select='not(between(n, start_frame, end_frame))',setpts=N/FRAME_RATE/TB"
```

---

## 8. Client BioChroma Subtitle Standards (Strict Compliance)

Over the entire assembled video, captions are burned in accordance with client standards:
* **Typography**: **Roboto Bold** (`Roboto-Bold.ttf`) at **`78 pt`** (`Bold: -1`).
* **Styling**: Pure white text (`#FFFFFF`) with a crisp **`4.0 pt`** dark outline (`#181818`), `Shadow: 0`, letter-spacing `0.5 pt`.
* **Motion**: **Completely Static**. NO kinetic bounce, NO karaoke word-coloring, NO pop-up scales, NO fade transitions.
* **Row Restriction**: **Strict Single Horizontal Row** (`WrapStyle: 2`). Never wrap lines or stack rows.
* **Vertical Safe Zone**: Lower-middle third safe zone (**`MarginV: 520`**, ~27% from bottom edge). Clears platform seekbars while staying below the speaker's face and chest.
* **Script Accuracy**: 100% verbatim matching of the client's official Italian script using DP alignment with Whisper ASR. Locked terms: `BioChroma`, `Centella Asiatica`, `Peptidi di Seta`, `Peptidi Dorati`, `skincare`, `retinolo`, `botox`, `filler`, `lifting`.
* **Audio Passthrough**: Copy audio bit-for-bit (`-c:a copy`). Never compress or distort original voiceover tracks.

---

## 9. Step-by-Step Execution Guide

### Step 1: Ingest Files
Place your assets into `Input/`:
* `Input/competitor_ad.mp4`: The winning competitor reference video.
* `Input/biochroma_voiceover.mp3`: The client's Italian voiceover.

### Step 2: (Optional) Review & Confirm Exact Cut Frames
```powershell
.\.venv\Scripts\python.exe skills/biochroma-captions/scripts/reskin_competitor_ad.py review-cuts `
  --competitor "Input/competitor_ad.mp4"
```
Inspect the 4-frame review photos in `preview_frames/cuts_review/` to visually verify the exact start and end frame of every product/texture shot.

### Step 3: Run Autonomous Reskin Pipeline
```powershell
.\.venv\Scripts\python.exe skills/biochroma-captions/scripts/reskin_competitor_ad.py `
  --competitor "Input/competitor_ad.mp4" `
  --voiceover "Input/biochroma_voiceover.mp3" `
  --product-cuts "14.2-18.5, 32.0-36.4" `
  --output-dir "Output/biochroma_reskin_project_01"
```

### Step 4: Review the Storyboard & Preview
1. Open `Output/biochroma_reskin_project_01/rough_cut_preview.mp4` to watch the rough cut with Italian audio and 78pt captions.
2. Open `STORYBOARD_GUIDE.md` to review the English translations and AI prompts for all placeholders.

### Step 5: Manual Editing / AI Video Replacement
* **In CapCut / Premiere / Resolve**: Drag all clips from `clips/` onto your timeline with `00_master_voiceover.mp3`.
* Generate your replacement AI video clips (Kling / Runway) using the prompts provided in `STORYBOARD_GUIDE.md`.
* Drop the generated clips directly on top of the placeholder clips.

### Step 6: Final Master Render
Run the assembly command to stitch your final clips and burn the official client captions:
```powershell
.\.venv\Scripts\python.exe skills/biochroma-captions/scripts/reskin_competitor_ad.py assemble `
  --project-dir "Output/biochroma_reskin_project_01" `
  --output "Output/BioChroma_Master_Italian_Ad.mp4"
```

---

## 9. Summary of Benefits for the Editor

* **No Italian required**: The bilingual storyboard eliminates the language barrier completely.
* **No pacing headaches**: Clips and placeholders are pre-cut to match spoken words down to the microsecond.
* **Total creative freedom**: You can edit manually in your favorite editing software with zero friction.
* **Guaranteed client approval**: 100% adherence to BioChroma’s 78pt Roboto-Bold static caption standard and verbatim script alignment.

