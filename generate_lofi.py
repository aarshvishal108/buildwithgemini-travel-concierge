import math
import struct
import wave

SAMPLE_RATE = 44100
DURATION_SEC = 25  # 25 seconds of upbeat lo-fi music

def note_freq(note_name):
    notes = {'C3': 130.81, 'E3': 164.81, 'G3': 196.00, 'B3': 246.94,
             'A2': 110.00, 'C4': 261.63, 'E4': 329.63, 'G4': 392.00,
             'D3': 146.83, 'F3': 174.61, 'A3': 220.00, 'D4': 293.66,
             'G2': 98.00, 'B2': 123.47, 'D3': 146.83, 'F3': 174.61}
    return notes.get(note_name, 220.0)

# Upbeat Lo-Fi Chords: Cmaj7 -> Am7 -> Dm7 -> G7
CHORDS = [
    [130.81, 164.81, 196.00, 246.94], # Cmaj7
    [110.00, 130.81, 164.81, 196.00], # Am7
    [146.83, 174.61, 220.00, 293.66], # Dm7
    [98.00,  123.47, 146.83, 174.61]  # G7
]

def generate_samples():
    num_samples = int(SAMPLE_RATE * DURATION_SEC)
    samples = []
    
    bpm = 84
    beat_sec = 60.0 / bpm
    bar_sec = beat_sec * 4
    
    import random
    random.seed(42)
    
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        bar_idx = int(t / bar_sec) % len(CHORDS)
        current_chord = CHORDS[bar_idx]
        t_bar = t % bar_sec
        t_beat = t % beat_sec
        beat_num = int(t_bar / beat_sec)
        
        # 1. Soft Warm Synth Chords (Rhodes-like soft sine blend)
        chord_val = 0.0
        for freq in current_chord:
            # Soft sine with subtle vibrato
            vibrato = math.sin(2 * math.pi * 5.0 * t) * 0.8
            val = math.sin(2 * math.pi * (freq + vibrato) * t)
            # Add warm 2nd harmonic
            val += 0.3 * math.sin(2 * math.pi * (freq * 2.0) * t)
            chord_val += val
        chord_val *= 0.12 * math.exp(-1.5 * (t_bar % (beat_sec * 2)))
        
        # 2. Warm Bassline
        root_freq = current_chord[0] / 2.0  # sub bass
        bass_val = math.sin(2 * math.pi * root_freq * t) + 0.3 * math.sin(2 * math.pi * root_freq * 2 * t)
        bass_env = math.exp(-2.0 * t_beat)
        bass_val *= 0.25 * bass_env
        
        # 3. Upbeat Lo-Fi Beat (Kick on 1 & 3, Snare/Clap on 2 & 4, Hi-Hat on 8ths)
        beat_val = 0.0
        # Kick drum (frequency drop sine)
        if beat_num in (0, 2):
            kick_t = t_beat
            if kick_t < 0.15:
                kick_freq = 120.0 * math.exp(-35.0 * kick_t) + 40.0
                kick_val = math.sin(2 * math.pi * kick_freq * kick_t) * math.exp(-15.0 * kick_t)
                beat_val += kick_val * 0.45
                
        # Soft Snare / Rimshot on beat 2 & 4
        if beat_num in (1, 3):
            snare_t = t_beat
            if snare_t < 0.15:
                noise = (random.random() * 2.0 - 1.0) * math.exp(-25.0 * snare_t)
                tone = math.sin(2 * math.pi * 180.0 * snare_t) * math.exp(-30.0 * snare_t)
                beat_val += (noise * 0.25 + tone * 0.15)
                
        # Soft Hi-Hat on every 8th note
        t_eighth = t % (beat_sec / 2.0)
        if t_eighth < 0.05:
            hh_noise = (random.random() * 2.0 - 1.0) * math.exp(-60.0 * t_eighth)
            beat_val += hh_noise * 0.08

        # 4. Vinyl Hiss / Atmosphere
        vinyl = (random.random() * 2.0 - 1.0) * 0.012

        # Master Mix & Soft Clipping
        total = chord_val + bass_val + beat_val + vinyl
        total = max(-0.95, min(0.95, total))
        
        # Fade in & Fade out
        if t < 1.0:
            total *= t
        elif t > DURATION_SEC - 1.5:
            total *= (DURATION_SEC - t) / 1.5
            
        int_sample = int(total * 32767.0)
        samples.append(int_sample)
        
    return samples

def write_wav(filename, samples):
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        for s in samples:
            wav_file.writeframes(struct.pack('<h', s))

if __name__ == '__main__':
    print("Generating upbeat lo-fi track...")
    s = generate_samples()
    write_wav("lofi_track.wav", s)
    print("Generated lofi_track.wav successfully!")
