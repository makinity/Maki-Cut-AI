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
4. **Visual Semantic Alignment Standards**:
   * **"Our Little Secret" Punchline**: Whenever the spoken line is *"BioChroma, il nostro piccolo segreto"* (*"BioChroma, our little secret"*), the visual MUST show the iconic character close-up winking/smiling at the camera (`68.57s – 71.40s` for Row 16, `141.70s – 143.50s` for Row 35). NEVER replace these shots with placeholder slates—they are clean lifestyle character acting with zero competitor branding.
   * **"Send Me The Link" Product Action**: Whenever the spoken line is *"Ho detto: “Mandami il link.”"* (*"I said: “Send me the link.”"*), the visual MUST show the smartphone screen with the product link being tapped (`109.30s – 111.30s`).

