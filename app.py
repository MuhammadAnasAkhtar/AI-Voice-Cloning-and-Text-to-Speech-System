"""
Voice Studio — Premium TTS Web Application
Backend server with Flask. Run: python app.py
Open: http://127.0.0.1:5000
"""

import asyncio
import os
import pickle
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback

import numpy as np
import librosa
import soundfile as sf
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# ── App Setup ─────────────────────────────────────────────
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB upload limit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'uploads')
OUTPUT_DIR = os.path.join(BASE_DIR, 'static', 'output')
PROFILES_DIR = os.path.join(BASE_DIR, 'profiles')
PROFILES_FILE = os.path.join(PROFILES_DIR, 'voice_profiles.pkl')

ALLOWED_AUDIO = {'.wav', '.mp3', '.ogg', '.m4a', '.opus', '.webm', '.flac', '.aac'}

for d in (UPLOAD_DIR, OUTPUT_DIR, PROFILES_DIR):
    os.makedirs(d, exist_ok=True)

# ══════════════════════════════════════════════════════════
# VOICE / LANGUAGE DATA (from notebook)
# ══════════════════════════════════════════════════════════

LANG_VOICES = {
    'English': {
        'US - Andrew (Natural)':    {'v': 'en-US-AndrewNeural',      'for_identity': True},
        'US - Christopher':         {'v': 'en-US-ChristopherNeural', 'for_identity': True},
        'US - Guy (Deep)':          {'v': 'en-US-GuyNeural',         'for_identity': True},
        'US - Jenny':               {'v': 'en-US-JennyNeural',       'for_identity': True},
        'US - Aria':                {'v': 'en-US-AriaNeural',        'for_identity': True},
        'UK - Ryan':                {'v': 'en-GB-RyanNeural',        'for_identity': True},
        'UK - Thomas':              {'v': 'en-GB-ThomasNeural',      'for_identity': True},
        'UK - Sonia':               {'v': 'en-GB-SoniaNeural',       'for_identity': True},
        'Australia - William':      {'v': 'en-AU-WilliamNeural',     'for_identity': True},
        'Australia - Natasha':      {'v': 'en-AU-NatashaNeural',     'for_identity': True},
        'Ireland - Connor':         {'v': 'en-IE-ConnorNeural',      'for_identity': True},
        'India - Prabhat':          {'v': 'en-IN-PrabhatNeural',     'for_identity': True},
    },
    'Urdu': {
        'Pakistan - Asad':          {'v': 'ur-PK-AsadNeural',        'for_identity': True},
        'Pakistan - Uzma':          {'v': 'ur-PK-UzmaNeural',        'for_identity': True},
    },
    'Uzbek': {
        'Uzbekistan - Madina':      {'v': 'uz-UZ-MadinaNeural',      'for_identity': True},
        'Uzbekistan - Timur':       {'v': 'uz-UZ-TimurNeural',       'for_identity': True},
        'Uzbekistan - Dilshod':     {'v': 'uz-UZ-DilshodNeural',     'for_identity': True},
        'Uzbekistan - Nodira':      {'v': 'uz-UZ-NodiraNeural',      'for_identity': True},
        'Uzbekistan - Aziz':        {'v': 'uz-UZ-AzizNeural',        'for_identity': True},
    },
    'Arabic': {
        'Saudi Arabia - Hamed':     {'v': 'ar-SA-HamedNeural',       'for_identity': False},
        'Egypt - Salma':            {'v': 'ar-EG-SalmaNeural',       'for_identity': False},
        'UAE - Hajar':              {'v': 'ar-AE-HajarNeural',       'for_identity': False},
    },
    'Hindi': {
        'India - Madhur':           {'v': 'hi-IN-MadhurNeural',      'for_identity': False},
        'India - Swara':            {'v': 'hi-IN-SwaraNeural',       'for_identity': False},
    },
    'French': {
        'France - Henri':           {'v': 'fr-FR-HenriNeural',       'for_identity': False},
        'France - Denise':          {'v': 'fr-FR-DeniseNeural',      'for_identity': False},
        'Canada - Antoine':         {'v': 'fr-CA-AntoineNeural',     'for_identity': False},
    },
    'Spanish': {
        'Spain - Alvaro':           {'v': 'es-ES-AlvaroNeural',      'for_identity': False},
        'Mexico - Jorge':           {'v': 'es-MX-JorgeNeural',       'for_identity': False},
    },
    'German': {
        'Germany - Conrad':         {'v': 'de-DE-ConradNeural',      'for_identity': False},
        'Germany - Katja':          {'v': 'de-DE-KatjaNeural',       'for_identity': False},
    },
    'Turkish': {
        'Turkey - Ahmet':           {'v': 'tr-TR-AhmetNeural',       'for_identity': False},
    },
    'Persian': {
        'Iran - Farid':             {'v': 'fa-IR-FaridNeural',       'for_identity': False},
    },
    'Chinese': {
        'Mandarin - Yunxi':         {'v': 'zh-CN-YunxiNeural',       'for_identity': False},
        'Mandarin - Xiaoyi':        {'v': 'zh-CN-XiaoyiNeural',      'for_identity': False},
    },
    'Japanese': {
        'Japan - Keita':            {'v': 'ja-JP-KeitaNeural',       'for_identity': False},
        'Japan - Nanami':           {'v': 'ja-JP-NanamiNeural',      'for_identity': False},
    },
    'Korean': {
        'Korea - InJoon':           {'v': 'ko-KR-InJoonNeural',      'for_identity': False},
    },
    'Russian': {
        'Russia - Dmitry':          {'v': 'ru-RU-DmitryNeural',      'for_identity': True},
        'Russia - Svetlana':        {'v': 'ru-RU-SvetlanaNeural',    'for_identity': True},
        'Russia - Ivan':            {'v': 'ru-RU-IvanNeural',        'for_identity': True},
        'Russia - Olga':            {'v': 'ru-RU-OlgaNeural',        'for_identity': True},
        'Russia - Marina':          {'v': 'ru-RU-MarinaNeural',      'for_identity': True},
    },
}

STYLE_PRESETS = {
    'Natural':      {'rate': '+0%',  'pitch': '+0Hz',  'volume': '+10%'},
    'Newsreader':   {'rate': '+2%',  'pitch': '-1Hz',  'volume': '+12%'},
    'Narrator':     {'rate': '-3%',  'pitch': '+0Hz',  'volume': '+8%'},
    'Documentary':  {'rate': '-5%',  'pitch': '-3Hz',  'volume': '+10%'},
    'Professional': {'rate': '+1%',  'pitch': '-1Hz',  'volume': '+8%'},
    'Calm':         {'rate': '-8%',  'pitch': '-3Hz',  'volume': '-3%'},
    'Energetic':    {'rate': '+10%', 'pitch': '+4Hz',  'volume': '+18%'},
    'Dramatic':     {'rate': '-4%',  'pitch': '-2Hz',  'volume': '+6%'},
    'Cheerful':     {'rate': '+8%',  'pitch': '+6Hz',  'volume': '+15%'},
    'Emotional':    {'rate': '-6%',  'pitch': '-2Hz',  'volume': '+5%'},
}

# ══════════════════════════════════════════════════════════
# AUDIO HELPERS  (from notebook)
# ══════════════════════════════════════════════════════════

def _has_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

HAS_FFMPEG = _has_ffmpeg()

def convert_to_wav(src, sr=22050):
    ext = os.path.splitext(src)[1].lower()
    if ext == '.wav':
        return src
    out = src.rsplit('.', 1)[0] + '_conv.wav'
    # Try ffmpeg first (handles all formats)
    if HAS_FFMPEG:
        r = subprocess.run(
            ['ffmpeg', '-y', '-i', src, '-ar', str(sr), '-ac', '1', out],
            capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
            return out
    # Fallback: use librosa (handles mp3, ogg, flac, etc. via soundfile/audioread)
    try:
        y, orig_sr = librosa.load(src, sr=sr, mono=True)
        sf.write(out, y, sr)
        return out
    except Exception as e:
        raise RuntimeError(
            f'Cannot convert {ext} to WAV. '
            f'Install ffmpeg for best compatibility, or use WAV/MP3 files. '
            f'Error: {e}')


def clean_audio(y, sr, noise_strength=1.2, reverb_strength=0.3):
    import noisereduce as nr
    y = y.astype(np.float32)
    try:
        from scipy.signal import butter, sosfilt
        sos = butter(4, 80 / (sr / 2), btype='high', output='sos')
        y = sosfilt(sos, y).astype(np.float32)
    except Exception:
        pass
    noise_sample = y[:int(sr * 0.5)] if len(y) > sr else y
    y = nr.reduce_noise(
        y=y, sr=sr, y_noise=noise_sample,
        prop_decrease=noise_strength, stationary=False
    ).astype(np.float32)
    try:
        S = librosa.stft(y)
        mag, phase = np.abs(S), np.angle(S)
        reverb_est = np.minimum(
            mag, np.roll(mag, int(sr * 0.05 / 512), axis=1) * reverb_strength)
        mag = np.maximum(mag - reverb_est, 0)
        y = librosa.istft(mag * np.exp(1j * phase)).astype(np.float32)
    except Exception:
        pass
    y, _ = librosa.effects.trim(y, top_db=25)
    pk = np.max(np.abs(y))
    if pk > 0:
        y = y / pk * 0.89
    return y


def split_text(text, max_chars=900):
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    paragraphs = re.split(r'\n\s*\n', text)
    chunks, current = [], ''
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= max_chars:
            current = (current + '\n\n' + para).strip()
        else:
            if current:
                chunks.append(current)
            if len(para) > max_chars:
                sentences = re.split(r'(?<=[.!?;:\u0964\u06D4])\s+', para)
                current = ''
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= max_chars:
                        current = (current + ' ' + sent).strip()
                    else:
                        if current:
                            chunks.append(current)
                        if len(sent) > max_chars:
                            words = sent.split()
                            current = ''
                            for w in words:
                                if len(current) + len(w) + 1 <= max_chars:
                                    current = (current + ' ' + w).strip()
                                else:
                                    if current:
                                        chunks.append(current)
                                    current = w
                        else:
                            current = sent
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks if chunks else [text]


def merge_wavs(wav_files, out_path, sr=22050):
    gap = np.zeros(int(sr * 0.3), dtype=np.float32)
    combined = []
    for wf in wav_files:
        y, _ = librosa.load(wf, sr=sr, mono=True)
        combined.append(y.astype(np.float32))
        combined.append(gap)
    if not combined:
        sf.write(out_path, np.zeros(sr, dtype=np.float32), sr)
        return
    audio = np.concatenate(combined)
    pk = np.max(np.abs(audio))
    if pk > 0:
        audio = audio / pk * 0.92
    sf.write(out_path, audio, sr)


# ── TTS ───────────────────────────────────────────────────

def run_tts(voice, text, rate, pitch, volume, out_path):
    err = [None]

    def _run():
        try:
            import edge_tts
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                edge_tts.Communicate(
                    text=text, voice=voice,
                    rate=rate, pitch=pitch, volume=volume
                ).save(out_path)
            )
            loop.close()
        except Exception as e:
            err[0] = e

    t = threading.Thread(target=_run)
    t.start()
    t.join(timeout=120)
    if err[0]:
        raise RuntimeError('edge-tts error: ' + str(err[0]))
    if not os.path.exists(out_path) or os.path.getsize(out_path) < 500:
        raise RuntimeError('TTS produced empty file')


# ── Voice Profile ─────────────────────────────────────────

class VoiceProfile:
    def __init__(self, name, wav_path):
        self.name = name
        self.wav_path = wav_path
        self.created = time.strftime('%Y-%m-%d %H:%M')
        self.f0_median = 150.0
        self.f0_std = 30.0
        self.duration = 0.0
        self._extract()

    def _extract(self):
        try:
            y, sr = librosa.load(self.wav_path, sr=22050, mono=True)
            self.duration = len(y) / sr
            f0, _, _ = librosa.pyin(y, fmin=60, fmax=400, sr=sr)
            v = f0[~np.isnan(f0)]
            v = v[v > 0]
            if len(v) >= 5:
                self.f0_median = float(np.median(v))
                self.f0_std = float(np.std(v))
        except Exception as e:
            print('Feature extraction warning:', e)

    def to_dict(self):
        return {
            'name': self.name,
            'created': self.created,
            'f0_median': round(self.f0_median, 1),
            'f0_std': round(self.f0_std, 1),
            'duration': round(self.duration, 1),
        }


def load_profiles():
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception:
            pass
    return {}


def save_profiles(p):
    with open(PROFILES_FILE, 'wb') as f:
        pickle.dump(p, f)


# ── WORLD Voice Identity Transfer ─────────────────────────

def transfer_voice_identity(user_wav, tts_wav, out_wav,
                            timbre_amount=0.0, tempo_blend=0.0,
                            profile=None):
    import pyworld as pw
    SR = 22050
    FM = (256 / SR) * 1000

    def load64(p):
        y, _ = librosa.load(p, sr=SR, mono=True)
        return y.astype(np.float64)

    td = load64(tts_wav)
    tf0, tsp, tap = pw.wav2world(td, SR, frame_period=FM)

    if profile is not None:
        u_med, u_std = profile.f0_median, profile.f0_std
    else:
        ud = load64(user_wav)
        uf0, _, _ = pw.wav2world(ud, SR, frame_period=FM)
        v = uf0[uf0 > 0]
        u_med = float(np.median(v)) if len(v) >= 5 else 150.0
        u_std = float(np.std(v)) if len(v) >= 5 else 30.0

    tv = tf0[tf0 > 0]
    t_med = float(np.median(tv)) if len(tv) >= 5 else 150.0
    t_std = float(np.std(tv)) if len(tv) >= 5 else 1.0
    if t_std < 1e-3:
        t_std = 1.0

    nf0 = tf0.copy()
    mask = tf0 > 0
    nf0[mask] = np.clip((tf0[mask] - t_med) / t_std * u_std + u_med, 60, 500)

    if timbre_amount > 0.01 and user_wav and os.path.exists(user_wav):
        ud = load64(user_wav)
        _, usp, _ = pw.wav2world(ud, SR, frame_period=FM)
        nt, nf = tsp.shape
        nu = usp.shape[0]
        if nu != nt:
            xu = np.linspace(0, 1, nu)
            xt = np.linspace(0, 1, nt)
            usp_r = np.zeros((nt, nf))
            for k in range(nf):
                usp_r[:, k] = np.interp(xt, xu, usp[:, k])
        else:
            usp_r = usp
        tsp = np.clip(timbre_amount * usp_r + (1 - timbre_amount) * tsp, 1e-20, None)

    synth = pw.synthesize(
        nf0.astype(np.float64),
        np.clip(tsp, 1e-20, None).astype(np.float64),
        tap.astype(np.float64), SR, frame_period=FM)

    if tempo_blend > 0.05 and user_wav and os.path.exists(user_wav):
        ud = load64(user_wav)
        r = float(np.clip(
            1 + (len(ud) / SR / max(len(td) / SR, 0.1) - 1) * tempo_blend,
            0.75, 1.4))
        if abs(r - 1) > 0.05:
            synth = librosa.effects.time_stretch(
                synth.astype(np.float32), rate=r
            ).astype(np.float64)

    pk = np.max(np.abs(synth))
    if pk > 0:
        synth = synth / pk * 0.92
    sf.write(out_wav, synth.astype(np.float32), SR)


# ══════════════════════════════════════════════════════════
# FLASK ROUTES
# ══════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/languages')
def api_languages():
    data = {}
    for lang, accents in LANG_VOICES.items():
        data[lang] = list(accents.keys())
    return jsonify({
        'languages': data,
        'styles': list(STYLE_PRESETS.keys()),
    })


@app.route('/api/profiles')
def api_profiles():
    profiles = load_profiles()
    return jsonify({
        'profiles': [p.to_dict() for p in profiles.values()]
    })


@app.route('/api/upload-voice', methods=['POST'])
def api_upload_voice():
    if 'audio' not in request.files:
        return jsonify({'ok': False, 'error': 'No audio file uploaded'}), 400

    file = request.files['audio']
    name = request.form.get('name', '').strip()
    noise = float(request.form.get('noise', 1.2))
    reverb = float(request.form.get('reverb', 0.3))

    if not name:
        return jsonify({'ok': False, 'error': 'Profile name is required'}), 400

    if not file.filename:
        return jsonify({'ok': False, 'error': 'No file selected'}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_AUDIO:
        return jsonify({'ok': False, 'error': f'Unsupported format: {ext}'}), 400

    # Save uploaded file
    safe_name = secure_filename(file.filename)
    upload_path = os.path.join(UPLOAD_DIR, f'{int(time.time())}_{safe_name}')
    file.save(upload_path)

    try:
        wav_path = convert_to_wav(upload_path)
        y, sr = librosa.load(wav_path, sr=22050, mono=True)
        y_clean = clean_audio(y, sr, noise, reverb)

        profile_wav = os.path.join(
            PROFILES_DIR,
            f'profile_{name.lower().replace(" ", "_")}.wav')
        sf.write(profile_wav, y_clean, 22050)

        profile = VoiceProfile(name, profile_wav)
        profiles = load_profiles()
        profiles[name] = profile
        save_profiles(profiles)

        return jsonify({
            'ok': True,
            'profile': profile.to_dict(),
            'message': f'Profile "{name}" saved successfully!'
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    finally:
        # Cleanup uploaded raw file
        try:
            os.remove(upload_path)
        except Exception:
            pass


@app.route('/api/delete-profile', methods=['POST'])
def api_delete_profile():
    name = request.json.get('name', '')
    profiles = load_profiles()
    if name in profiles:
        try:
            os.remove(profiles[name].wav_path)
        except Exception:
            pass
        del profiles[name]
        save_profiles(profiles)
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Profile not found'}), 404


@app.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.json or {}
    text = data.get('text', '').strip()
    lang = data.get('lang', 'English')
    accent = data.get('accent', '')
    style = data.get('style', 'Natural')
    prof_name = data.get('profile', '')
    timbre = float(data.get('timbre', 0.0))
    tempo = float(data.get('tempo', 0.0))
    pitch_sc = float(data.get('pitch', 1.0))
    mode = data.get('mode', 'clone')  # 'clone' or 'normal'

    if not text:
        return jsonify({'ok': False, 'error': 'Text is empty'}), 400

    words = len(text.split())
    if words > 100000:
        return jsonify({'ok': False, 'error': f'Text has {words:,} words. Limit is 100,000.'}), 400

    if lang not in LANG_VOICES:
        return jsonify({'ok': False, 'error': f'Language "{lang}" not found'}), 400
    if accent not in LANG_VOICES.get(lang, {}):
        return jsonify({'ok': False, 'error': f'Accent "{accent}" not found'}), 400
    if style not in STYLE_PRESETS:
        style = 'Natural'

    voice_entry = LANG_VOICES[lang][accent]
    voice = voice_entry['v']
    do_identity = voice_entry.get('for_identity', False) and mode == 'clone'
    style_p = STYLE_PRESETS[style]

    profile = None
    if mode == 'clone':
        profiles = load_profiles()
        if not profiles:
            return jsonify({'ok': False, 'error': 'No voice profile. Upload one first.'}), 400
        if prof_name not in profiles:
            prof_name = list(profiles.keys())[0]
        profile = profiles[prof_name]

    try:
        ts = int(time.time())
        chunks = split_text(text)
        total = len(chunks)
        chunk_wavs = []

        for i, chunk in enumerate(chunks):
            tts_mp3 = os.path.join(OUTPUT_DIR, f'tts_{ts}_{i}.mp3')
            run_tts(voice, chunk, style_p['rate'], style_p['pitch'], style_p['volume'], tts_mp3)
            tts_wav = convert_to_wav(tts_mp3)

            if do_identity and profile:
                out_wav = os.path.join(OUTPUT_DIR, f'chunk_{ts}_{i}.wav')
                try:
                    transfer_voice_identity(
                        profile.wav_path, tts_wav, out_wav,
                        timbre_amount=timbre, tempo_blend=tempo,
                        profile=profile)
                    if abs(pitch_sc - 1.0) > 0.02:
                        y, sr = librosa.load(out_wav, sr=22050)
                        y = librosa.effects.pitch_shift(
                            y, sr=sr, n_steps=float(12.0 * np.log2(pitch_sc)))
                        sf.write(out_wav, y, sr)
                    chunk_wavs.append(out_wav)
                except Exception:
                    chunk_wavs.append(tts_wav)
            else:
                chunk_wavs.append(tts_wav)

        safe = re.sub(r'[^a-z0-9]', '_', (prof_name or 'voice').lower())
        fwav = os.path.join(OUTPUT_DIR, f'final_{safe}_{ts}.wav')
        fmp3 = fwav.replace('.wav', '.mp3')

        if len(chunk_wavs) == 1:
            shutil.copy2(chunk_wavs[0], fwav)
        else:
            merge_wavs(chunk_wavs, fwav)

        if HAS_FFMPEG:
            subprocess.run(['ffmpeg', '-y', '-i', fwav, '-q:a', '2', fmp3], capture_output=True)
        final = fmp3 if os.path.exists(fmp3) and os.path.getsize(fmp3) > 0 else fwav
        final_name = os.path.basename(final)

        # Duration
        try:
            y_f, sr_f = librosa.load(final, sr=None, mono=True)
            dur = len(y_f) / sr_f
            dur_str = f'{int(dur // 60)}:{int(dur % 60):02d}'
        except Exception:
            dur_str = '—'

        size_kb = os.path.getsize(final) // 1024

        # Cleanup temp files
        for wf in chunk_wavs:
            try:
                if os.path.basename(wf).startswith(('tts_', 'chunk_')):
                    os.remove(wf)
            except Exception:
                pass

        id_label = 'Voice identity applied' if do_identity else 'Standard TTS voice'

        return jsonify({
            'ok': True,
            'filename': final_name,
            'url': f'/static/output/{final_name}',
            'duration': dur_str,
            'words': words,
            'chunks': total,
            'size_kb': size_kb,
            'identity': id_label,
            'profile': prof_name or '—',
            'lang': lang,
            'accent': accent,
            'style': style,
        })

    except Exception as e:
        tb = traceback.format_exc()
        error_message = str(e)
        # Uzbek edge-tts error audio fallback
        uzbek_error_voices = {
            'uz-UZ-TimurNeural',
            'uz-UZ-DilshodNeural',
            'uz-UZ-NodiraNeural',
            'uz-UZ-AzizNeural',
        }
        if 'edge-tts error: No audio was received' in error_message and voice in uzbek_error_voices:
            # Serve the default error audio file
            error_audio = os.path.join(OUTPUT_DIR, 'uzbek_edge_tts_error.mp3')
            if os.path.exists(error_audio):
                final_name = os.path.basename(error_audio)
                return jsonify({
                    'ok': True,
                    'filename': final_name,
                    'url': f'/static/output/{final_name}',
                    'duration': '—',
                    'words': words,
                    'chunks': 1,
                    'size_kb': os.path.getsize(error_audio) // 1024,
                    'identity': 'Error audio',
                    'profile': prof_name or '—',
                    'lang': lang,
                    'accent': accent,
                    'style': style,
                    'error': 'No audio was received from edge-tts. Returning default error audio.'
                })
        # Custom handling for edge-tts 'No audio was received' error (other voices)
        if 'edge-tts error: No audio was received' in error_message:
            user_message = (
                'No audio was received from the TTS engine. This may be due to invalid parameters (voice, text, rate, pitch, or volume), network issues, or a temporary service problem. '
                'Please check your input and try again. If the problem persists, try a different voice or style.'
            )
            return jsonify({'ok': False, 'error': user_message, 'details': error_message, 'traceback': tb}), 500
        # Default error handling
        return jsonify({'ok': False, 'error': error_message, 'traceback': tb}), 500


# ══════════════════════════════════════════════════════════
# RUN SERVER
# ══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print()
    print('=' * 55)
    print('  Voice Studio Server')
    print('  Open: http://127.0.0.1:5000')
    print('=' * 55)
    print()
    app.run(host='127.0.0.1', port=5000, debug=False)
