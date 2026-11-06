# Workspace Rules & Client Standards

## Client BioChroma Ad Captions

When the user asks to **"put a caption for biochroma ad"**, **"caption this biochroma ad"**, or references **"BioChroma"**:
- **Activate Skill**: Use `skills/biochroma-captions/SKILL.md` (or `.agents/skills/biochroma-captions/SKILL.md`).
- **Autonomous CLI Command**:
  ```powershell
  # Standard 78pt caption generator:
  .\.venv\Scripts\python.exe skills/biochroma-captions/scripts/generate_biochroma_captions.py

  # Video 2 Reskin Pipeline (40-row semantic beat cut & placeholders):
  .\.venv\Scripts\python.exe skills/biochroma-captions/scripts/reskin_video2.py
  ```
- **Strict Client Specifications**:
  1. **Typography**: **Roboto Bold** (`Roboto-Bold.ttf`) at **`78 pt`** on 1080×1920 reference canvas (`Bold: -1`).
  2. **Styling**: Pure white text (`#FFFFFF`) with a thin, crisp **`4.0 pt`** dark outline (`#181818`), `Shadow: 0`, letter-spacing `0.5 pt`.
  3. **Motion**: Completely static. NO kinetic bounce, NO karaoke word-coloring, NO pop-up scales, NO fade transitions.
  4. **Row Restriction**: **Strict Single Horizontal Row** (`WrapStyle: 2`). Never wrap lines or stack rows.
  5. **Vertical Placement**: Lower-middle third safe zone (`MarginV: 520`, ~27% from bottom edge). Clears native platform seekbars/UI while staying below faces and chests.
  6. **Script Alignment**: 100% verbatim matching of the client's official Italian script using DP alignment with Whisper ASR. Locked terms: `BioChroma`, `Centella Asiatica`, `Peptidi di Seta`, `Peptidi Dorati`, `skincare`, `retinolo`, `botox`, `filler`, `lifting`.
  7. **Audio Preservation**: Copy audio bit-for-bit (`-c:a copy`). Never re-encode or compress original audio tracks.
  8. **Visual Semantic Alignment Standards**:
     - **"Our Little Secret" Punchline**: Whenever the script speaks *"BioChroma, il nostro piccolo segreto"* (*"BioChroma, our little secret"*), the visual MUST show the iconic character close-up winking/smiling at the camera (`68.57s – 71.40s` for Row 16, `141.70s – 143.50s` for Row 35). NEVER replace these shots with placeholder slates—they are clean lifestyle character acting with zero competitor branding.
     - **"Send Me The Link" Product Action**: Whenever the spoken line is *"Ho detto: “Mandami il link.”"* (*"I said: “Send me the link.”"*), the visual MUST show the smartphone screen with the product link being tapped (`109.30s – 111.30s`).

