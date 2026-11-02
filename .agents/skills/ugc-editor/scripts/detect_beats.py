#!/usr/bin/env python3
"""
CapCut-Style Auto-Beat Detection & Rhythm Analysis Engine.
Analyzes music tracks and audio to extract:
- Major Downbeats (Beat 1: Kicks, primary rhythmic pulse)
- Sub-Rhythms (Beat 2: Faster 1/8th note beats, snares, off-beats)
- Estimated BPM (Tempo)
- Waveform Envelope Samples for visual timeline rendering
- Snap-to-Beat quantization helpers for cuts and transitions
"""

import sys
import os
import json
import math
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

import numpy as np
import scipy.signal

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def extract_pcm_samples(audio_path: Path, target_sr: int = 22050):
    """Extract raw 16-bit mono PCM samples via FFmpeg."""
    ffmpeg_exe = str(Path(sys.prefix) / "Scripts" / "ffmpeg.exe")
    if not Path(ffmpeg_exe).exists():
        ffmpeg_exe = "ffmpeg"

    cmd = [
        ffmpeg_exe, "-v", "error",
        "-i", str(audio_path),
        "-ac", "1",
        "-ar", str(target_sr),
        "-f", "s16le",
        "-"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    raw_bytes = proc.stdout
    samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, target_sr

def analyze_audio_beats(audio_path: Path, max_duration: float = 120.0) -> Dict[str, Any]:
    """Analyzes audio rhythm, returning Beat 1, Beat 2, BPM, and Waveform Envelopes."""
    samples, sr = extract_pcm_samples(audio_path, target_sr=22050)
    
    total_len = len(samples)
    duration = total_len / sr
    if duration > max_duration:
        samples = samples[:int(max_duration * sr)]
        duration = max_duration

    # 1. Bandpass filter for low-end punch (45Hz - 180Hz) to isolate kicks & bass rhythm
    sos_bass = scipy.signal.butter(4, [45, 180], btype='bandpass', fs=sr, output='sos')
    bass_filtered = scipy.signal.sosfilt(sos_bass, samples)
    bass_env = np.abs(bass_filtered)

    # Smooth the bass envelope with a 40ms sliding window
    win_len = int(sr * 0.04)
    bass_smooth = np.convolve(bass_env, np.ones(win_len) / win_len, mode='same')

    # 2. Beat 1 Detection (Major downbeats / kicks):
    min_dist_b1 = int(sr * 0.34)
    h_thresh_b1 = float(np.mean(bass_smooth) + 0.30 * np.std(bass_smooth))
    peaks_b1, _ = scipy.signal.find_peaks(bass_smooth, distance=min_dist_b1, height=h_thresh_b1)
    beat1_times = [round(float(p) / sr, 3) for p in peaks_b1]

    # Calculate BPM from Beat 1 intervals
    if len(beat1_times) >= 3:
        diffs = np.diff(beat1_times)
        valid_diffs = diffs[(diffs >= 0.25) & (diffs <= 1.2)]
        if len(valid_diffs) > 0:
            median_interval = float(np.median(valid_diffs))
            bpm = round(60.0 / median_interval, 1)
        else:
            bpm = 120.0
    else:
        bpm = 120.0

    # 3. Beat 2 Detection (Sub-rhythms / faster 1/8 note beats & snares):
    sos_mid = scipy.signal.butter(3, [180, 2500], btype='bandpass', fs=sr, output='sos')
    mid_filtered = scipy.signal.sosfilt(sos_mid, samples)
    mid_env = np.abs(mid_filtered)
    combined_env = (bass_smooth * 0.6) + (mid_env * 0.4)
    
    min_dist_b2 = int(sr * 0.17)
    h_thresh_b2 = float(np.mean(combined_env) + 0.20 * np.std(combined_env))
    peaks_b2, _ = scipy.signal.find_peaks(combined_env, distance=min_dist_b2, height=h_thresh_b2)
    beat2_times = [round(float(p) / sr, 3) for p in peaks_b2]

    # 4. Normalized Waveform Peak Points (100 points for crisp visual SVG timeline rendering)
    num_points = 120
    chunk_size = max(1, len(samples) // num_points)
    waveform_points = []
    for i in range(num_points):
        chunk = samples[i * chunk_size : (i + 1) * chunk_size]
        if len(chunk) > 0:
            waveform_points.append(round(float(np.max(np.abs(chunk))), 3))
        else:
            waveform_points.append(0.0)

    # Scale waveform points to 0.1 - 1.0 range
    max_w = max(waveform_points) if waveform_points and max(waveform_points) > 0 else 1.0
    normalized_waveform = [round(w / max_w, 2) for w in waveform_points]

    return {
        "status": "ok",
        "filename": audio_path.name,
        "bpm": bpm,
        "duration": round(duration, 2),
        "beat1_major_count": len(beat1_times),
        "beat2_sub_count": len(beat2_times),
        "beat1_major": beat1_times,
        "beat2_sub": beat2_times,
        "waveform_envelope": normalized_waveform
    }

def snap_cut_to_nearest_beat(cut_time: float, beat_list: List[float], max_snap_distance: float = 0.40) -> float:
    """Snaps a video cut point to the nearest musical beat within tolerance."""
    if not beat_list:
        return cut_time
    closest_beat = min(beat_list, key=lambda b: abs(b - cut_time))
    if abs(closest_beat - cut_time) <= max_snap_distance:
        return closest_beat
    return cut_time

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CapCut-Style Auto-Beat Detector")
    parser.add_argument("-i", "--input", required=True, help="Path to audio or video file")
    parser.add_argument("-j", "--json", action="store_true", help="Output pure JSON")
    args = parser.parse_args()

    audio_file = Path(args.input)
    if not audio_file.exists():
        print(f"Error: File {audio_file} not found!", file=sys.stderr)
        sys.exit(1)

    result = analyze_audio_beats(audio_file)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"🎵 Audio Beat Analysis for '{result['filename']}':")
        print(f"   • Tempo: {result['bpm']} BPM")
        print(f"   • Duration: {result['duration']}s")
        print(f"   • Beat 1 (Major Downbeats): {result['beat1_major_count']} beats")
        print(f"   • Beat 2 (Sub-Rhythms): {result['beat2_sub_count']} beats")
        print(f"   • First 6 Major Beats: {result['beat1_major'][:6]}")
