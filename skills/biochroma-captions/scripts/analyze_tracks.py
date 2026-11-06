import json
from pathlib import Path
from faster_whisper import WhisperModel

def main():
    print("Loading Whisper model base...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    
    comp_video = "Input/Video 1 Cleaned.mp4"
    it_audio = "Input/Video 1 Musical - Mark.mp3"
    
    print(f"Transcribing competitor video: {comp_video}...")
    segments, info = model.transcribe(comp_video, word_timestamps=True)
    comp_results = []
    for s in segments:
        words = [{"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3)} for w in s.words]
        comp_results.append({
            "start": round(s.start, 3),
            "end": round(s.end, 3),
            "text": s.text.strip(),
            "words": words
        })
    with open("competitor_transcript.json", "w", encoding="utf-8") as f:
        json.dump(comp_results, f, indent=2, ensure_ascii=False)
        
    print(f"Transcribing Italian voiceover: {it_audio}...")
    it_segments, it_info = model.transcribe(it_audio, language="it", word_timestamps=True)
    it_results = []
    for s in it_segments:
        words = [{"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3)} for w in s.words]
        it_results.append({
            "start": round(s.start, 3),
            "end": round(s.end, 3),
            "text": s.text.strip(),
            "words": words
        })
    with open("italian_transcript.json", "w", encoding="utf-8") as f:
        json.dump(it_results, f, indent=2, ensure_ascii=False)
        
    print(f"Done. Competitor: {len(comp_results)} segments, Italian: {len(it_results)} segments.")

if __name__ == "__main__":
    main()

