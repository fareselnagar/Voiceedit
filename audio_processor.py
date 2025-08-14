
import os, json, tempfile, shutil
import numpy as np
import librosa, soundfile as sf
import noisereduce as nr
import pyloudnorm as pyln
from pydub import AudioSegment
from scipy.signal import butter, sosfilt
from math import ceil

# Optional heavy imports wrapped in try/except
try:
    from spleeter.separator import Separator
    _SPLEETER_OK = True
except Exception:
    _SPLEETER_OK = False

try:
    import demucs.separate as demucs_separate
    _DEMUCS_OK = True
except Exception:
    _DEMUCS_OK = False

# load presets
PRESETS_PATH = "presets.json"
if os.path.exists(PRESETS_PATH):
    with open(PRESETS_PATH, 'r', encoding='utf-8') as f:
        PRESETS = json.load(f)
else:
    PRESETS = {}

def list_presets():
    return list(PRESETS.keys()) if PRESETS else ["master_auto","podcast_voice","music_track"]

def to_wav(input_path, out_wav):
    AudioSegment.from_file(input_path).export(out_wav, format="wav")

def highpass(y, sr, cutoff=60, order=4):
    sos = butter(order, cutoff, btype='high', fs=sr, output='sos')
    return sosfilt(sos, y)

def multiband_eq(y, sr):
    # Simple multi-band EQ: reduce subsonic, tame lows, slight presence boost
    y = highpass(y, sr, cutoff=40)
    # apply a mild presence boost between 2k-6k
    # We approximate by boosting via FFT magnitude shaping (coarse)
    Y = np.fft.rfft(y)
    freqs = np.fft.rfftfreq(len(y), 1.0/sr)
    boost = 1.0 + 0.18 * np.exp(-((freqs-3000)**2)/(2*(2500**2)))
    Y *= boost
    y2 = np.fft.irfft(Y)
    return y2

def advanced_compress(y, sr, threshold_db=-18.0, ratio=4.0, attack_ms=10, release_ms=100):
    # very coarse adaptive RMS compressor
    eps = 1e-9
    frame_len = int(sr * 0.02)
    out = np.zeros_like(y)
    gain = 1.0
    alpha_a = np.exp(-1.0/(sr*(attack_ms/1000.0)))
    alpha_r = np.exp(-1.0/(sr*(release_ms/1000.0)))
    env = 0.0
    for i in range(0, len(y), frame_len):
        frame = y[i:i+frame_len]
        rms = np.sqrt(np.mean(frame**2)+eps)
        db = 20*np.log10(rms+eps)
        if db > threshold_db:
            target_gain_db = (threshold_db - db)*(1 - 1/ratio)
        else:
            target_gain_db = 0.0
        target_gain = 10**(target_gain_db/20.0)
        # smooth gain (simple)
        gain = gain*alpha_a + target_gain*(1-alpha_a)
        out[i:i+len(frame)] = frame * gain
    return out

def limiter(y, ceiling_db=-0.5):
    peak = np.max(np.abs(y)) + 1e-9
    peak_db = 20*np.log10(peak)
    if peak_db > ceiling_db:
        gain_db = ceiling_db - peak_db
        gain = 10**(gain_db/20.0)
        y = y * gain
    return np.clip(y, -0.9999, 0.9999)

def loudness_normalize(y, sr, target_lufs=-14.0):
    meter = pyln.Meter(sr)
    loudness = meter.integrated_loudness(y)
    gain_db = target_lufs - loudness
    y_out = pyln.normalize.loudness(y, loudness, target_lufs)
    return y_out

def denoise_with_demucs(input_path, out_path):
    # Very rough wrapper: only if demucs is available
    if not _DEMUCS_OK:
        raise RuntimeError("Demucs not available")
    # demucs separate -n mdx_extra_q input_path --out out_dir
    out_dir = os.path.splitext(out_path)[0] + "_demucs"
    os.makedirs(out_dir, exist_ok=True)
    # Use demucs CLI via python API if available (this section may need adjustments)
    demucs_separate.main([input_path, "--out", out_dir])
    # find vocals/stems and recombine or choose denoised stem
    # This is a placeholder; for now just return input_path
    return input_path

def process_file(input_path, output_path, preset="master_auto"):
    # ensure wav
    name, ext = os.path.splitext(input_path)
    tmp_wav = input_path if ext.lower()==".wav" else name + "_conv.wav"
    if ext.lower() != ".wav":
        to_wav(input_path, tmp_wav)

    y, sr = librosa.load(tmp_wav, sr=44100, mono=True)
    # Stage 1: optional source separation to improve denoising (uses spleeter if available)
    preset_cfg = PRESETS.get(preset, {})
    denoise_strength = preset_cfg.get("denoise_strength", "auto")

    if _SPLEETER_OK and denoise_strength in ("auto","high","medium"):
        try:
            sep = Separator('spleeter:2stems')
            # produce stems in a temp dir
            tempdir = tempfile.mkdtemp(prefix="spleet_")
            sep.separate_to_file(tmp_wav, tempdir)
            # locate vocal stem
            vocal_path = None
            for root, dirs, files in os.walk(tempdir):
                for f in files:
                    if f.endswith("vocals.wav"):
                        vocal_path = os.path.join(root, f)
                        break
            if vocal_path:
                y_v, _ = librosa.load(vocal_path, sr=sr, mono=True)
                # Denoise vocal separately
                y_v_dn = nr.reduce_noise(y=y_v, sr=sr)
                # reconstruct: mix denoised vocal with accompaniment
                # load accompaniment
                acc_path = vocal_path.replace("vocals.wav","accompaniment.wav")
                if os.path.exists(acc_path):
                    y_acc, _ = librosa.load(acc_path, sr=sr, mono=True)
                    # simple mix with reduced vocal artifacts
                    y = y_acc + y_v_dn
            shutil.rmtree(tempdir)
        except Exception as e:
            # fallback to regular denoise
            pass

    # Stage 2: robust noise reduction (noisereduce on entire signal)
    try:
        # pick a noise sample heuristically from quietest 0.5s portion
        frame_len = int(sr*0.5)
        if len(y) > frame_len:
            # choose chunk with lowest energy
            energies = [np.mean(np.abs(y[i:i+frame_len])) for i in range(0, len(y)-frame_len, frame_len)]
            min_idx = int(np.argmin(energies))*frame_len
            noise_sample = y[min_idx:min_idx+frame_len]
            y = nr.reduce_noise(y=y, y_noise=noise_sample, sr=sr, stationary=False)
        else:
            y = nr.reduce_noise(y=y, sr=sr, stationary=False)
    except Exception:
        pass

    # Stage 3: EQ
    y = multiband_eq(y, sr)

    # Stage 4: Compressor
    y = advanced_compress(y, sr, threshold_db=-18.0, ratio=3.5)

    # Stage 5: Loudness normalization to target LUFS
    target = preset_cfg.get("target_loudness", -14.0)
    try:
        y = loudness_normalize(y, sr, target_lufs=float(target))
    except Exception:
        pass

    # Stage 6: Limiter & final clamp
    y = limiter(y, ceiling_db=-0.5)

    # Save output
    sf.write(output_path, y, sr, subtype='PCM_24')
    return output_path
