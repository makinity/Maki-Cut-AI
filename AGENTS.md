# Workspace Rules & Client Standards

## Client BioChroma Ad Captions

When the user asks to **"put a caption for biochroma ad"**, **"caption this biochroma ad"**, or references **"BioChroma"**:
- **Activate Skill**: Use `skills/biochroma-captions/SKILL.md` (or `.agents/skills/biochroma-captions/SKILL.md`).
- **Autonomous CLI Command**:
  ```powershell
  .\.venv\Scripts\python.exe skills/biochroma-captions/scripts/generate_biochroma_captions.py
  ```
- **Strict Client Specifications**:
  1. **Typography**: **Roboto Bold** (`Roboto-Bold.ttf`) at **`78 pt`** on 1080×1920 reference canvas (`Bold: -1`).
  2. **Styling**: Pure white text (`#FFFFFF`) with a thin, crisp **`4.0 pt`** dark outline (`#181818`), `Shadow: 0`, letter-spacing `0.5 pt`.
  3. **Motion**: Completely static. NO kinetic bounce, NO karaoke word-coloring, NO pop-up scales, NO fade transitions.
  4. **Row Restriction**: **Strict Single Horizontal Row** (`WrapStyle: 2`). Never wrap lines or stack rows.
  5. **Vertical Placement**: Lower-middle third safe zone (`MarginV: 520`, ~27% from bottom edge). Clears native platform seekbars/UI while staying below faces and chests.
  6. **Script Alignment**: 100% verbatim matching of the client's official Italian script using DP alignment with Whisper ASR. Locked terms: `BioChroma`, `Centella Asiatica`, `Peptidi di Seta`, `Peptidi Dorati`, `skincare`, `retinolo`, `botox`, `filler`, `lifting`.
  7. **Audio Preservation**: Copy audio bit-for-bit (`-c:a copy`). Never re-encode or compress original audio tracks.

