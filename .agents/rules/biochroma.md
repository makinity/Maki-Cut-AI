---
trigger: model_decision
description: Enforce client BioChroma ad captioning standards, font styling, safe zone, and verbatim Italian alignment.
---

# Client BioChroma Ad Captioning Rule

When processing video ads for client **BioChroma** (e.g. "put a caption for biochroma ad", "caption this biochroma ad"):

1. **Activate Skill**: Use `biochroma-captions` (`skills/biochroma-captions/SKILL.md`).
2. **Execute Automation**:
   ```powershell
   .\.venv\Scripts\python.exe skills/biochroma-captions/scripts/generate_biochroma_captions.py -i "Input/<video>.mp4" -o "Output/<video>_captioned.mp4"
   ```
3. **Locked Client Styling**:
   * Font: **Roboto Bold** (`Roboto-Bold.ttf`)
   * Size: **78 pt** (on 1080×1920 reference canvas)
   * Weight: `Bold: -1`
   * Text Color: `#FFFFFF`
   * Stroke: `4.0 pt` dark outline (`#181818`), `Shadow: 0`
   * Motion: Completely static (clean cut-in, clean cut-out, no kinetic bounce, no karaoke)
   * Alignment & Safe Zone: Centered, lower-middle third (`MarginV: 520`, ~27% from bottom edge)
   * Single-Line Row: `WrapStyle: 2` (Zero line wrapping)
   * Script Alignment: Verbatim Italian dialogue via Needleman-Wunsch DP alignment
   * Audio: Copied bit-exact (`-c:a copy`)

