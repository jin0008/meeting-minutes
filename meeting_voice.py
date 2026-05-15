#!/usr/bin/env python3
"""
회의 녹음 + 화자 인식 + 자동 회의록 생성기

사용법:
  # 1. 목소리 등록 (교수님별 1회)
  python meeting_minutes.py enroll --part 주임교수 --file seo_voice.wav
  python meeting_minutes.py enroll --part 병원장              # 마이크로 직접 녹음

  # 2. 등록된 화자 목록 확인
  python meeting_minutes.py list

  # 3. 회의 진행 (녹음 + 화자 인식 + 회의록 생성)
  python meeting_minutes.py run --title "주간 교수회의" --api gemini
  python meeting_minutes.py run --file meeting.wav --title "월례회의" --api claude
"""

import os
import sys
import ssl
import json
import argparse
import datetime
import wave
import shutil
import numpy as np
from pathlib import Path

ssl._create_default_https_context = ssl._create_unverified_context

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")
WHISPER_MODEL     = "medium"
SAMPLE_RATE       = 16000
CHANNELS          = 1
PROFILES_DIR      = Path.home() / ".meeting_minutes" / "speaker_profiles"  # 홈 디렉토리에 영구 저장
SIMILARITY_THRESHOLD = 0.75                       # 화자 인식 최소 유사도 (0~1)

# ─────────────────────────────────────────────
# 고정 참석자
# ─────────────────────────────────────────────
# 보직 교수 (파트: 이름)
ROLE_PARTICIPANTS = {
    "주임교수": "서경률",
    "병원장":   "김찬윤",
    "총무":     "김태임",
    "부총무":   "고재상",
    "수련":     "김용준",
    "학생":     "윤진숙",
    "연구":     "한진우",
    "수술실":   "이승규",
    "외래":     "민지상",
    "인재개발": "전익현",
    "세목회":   "이지혜",
}

# 일반 교수 (보직 없음) — 이름이 곧 식별 키
GENERAL_PROFESSORS = ["김성수", "변석호", "배형원", "한재용", "곽지용", "김진영", "조진"]

# 전체 통합 딕셔너리 (키: 식별자, 값: 이름)
# 보직 교수는 "파트명" → "이름", 일반 교수는 "이름" → "이름"
PARTICIPANTS = {**ROLE_PARTICIPANTS, **{name: name for name in GENERAL_PROFESSORS}}

# 이름 → 파트(또는 이름) 역방향 조회
NAME_TO_PART = {v: k for k, v in PARTICIPANTS.items()}


# ─────────────────────────────────────────────
# 유틸: 오디오 로드 (16kHz mono float32)
# ─────────────────────────────────────────────
def load_audio(path: str) -> np.ndarray:
    """오디오 파일을 16kHz mono float32 numpy 배열로 로드합니다."""
    try:
        import librosa
        wav, _ = librosa.load(path, sr=SAMPLE_RATE, mono=True)
        return wav.astype(np.float32)
    except ImportError:
        pass

    # librosa 없을 경우 scipy 사용
    try:
        from scipy.io import wavfile
        sr, data = wavfile.read(path)
        if data.ndim > 1:
            data = data.mean(axis=1)
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            data = data.astype(np.float32) / 2147483648.0
        if sr != SAMPLE_RATE:
            # 간단한 리샘플링 (정확도 낮음)
            factor = SAMPLE_RATE / sr
            new_len = int(len(data) * factor)
            data = np.interp(
                np.linspace(0, len(data), new_len),
                np.arange(len(data)),
                data
            ).astype(np.float32)
        return data
    except Exception as e:
        print(f"❌ 오디오 로드 실패: {e}")
        print("   pip install librosa  또는  pip install scipy 를 설치해주세요.")
        sys.exit(1)


# ─────────────────────────────────────────────
# 1. 화자 등록 (Enrollment)
# ─────────────────────────────────────────────
def get_encoder():
    """resemblyzer Encoder를 반환합니다."""
    try:
        from resemblyzer import VoiceEncoder
        return VoiceEncoder()
    except ImportError:
        print("❌ resemblyzer가 설치되지 않았습니다: pip install resemblyzer")
        sys.exit(1)


def enroll_speaker(part: str, audio_path: str):
    """
    교수님 목소리를 등록합니다.
    part: 파트명 (예: '주임교수')
    audio_path: 목소리 샘플 오디오 파일 경로
    """
    if part not in PARTICIPANTS:
        print(f"❌ '{part}'은(는) 등록된 파트가 아닙니다.")
        print(f"   사용 가능한 파트: {', '.join(PARTICIPANTS.keys())}")
        sys.exit(1)

    name = PARTICIPANTS[part]
    print(f"\n🎤 [{part}] {name} 교수 목소리 등록 중...")

    encoder = get_encoder()
    wav = load_audio(audio_path)

    try:
        from resemblyzer import preprocess_wav
        wav = preprocess_wav(wav, source_sr=SAMPLE_RATE)
    except Exception:
        pass

    embedding = encoder.embed_utterance(wav)

    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profile_path = PROFILES_DIR / f"{part}.npy"
    np.save(str(profile_path), embedding)

    # 메타데이터 저장
    meta_path = PROFILES_DIR / "meta.json"
    meta = {}
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    meta[part] = {
        "name": name,
        "enrolled_at": datetime.datetime.now().isoformat(),
        "file": str(audio_path),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"✅ 등록 완료: {name} 교수 ({part}) → {profile_path}")


def load_profiles() -> dict:
    """저장된 화자 프로파일을 모두 불러옵니다. {part: embedding}"""
    profiles = {}
    if not PROFILES_DIR.exists():
        return profiles
    for npy_file in PROFILES_DIR.glob("*.npy"):
        part = npy_file.stem
        if part in PARTICIPANTS:
            profiles[part] = np.load(str(npy_file))
    return profiles


def list_enrolled():
    """등록된 화자 목록을 출력합니다."""
    print("\n📋 등록된 화자 목록")
    meta_path = PROFILES_DIR / "meta.json"
    meta = {}
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

    enrolled_count = 0
    total = len(PARTICIPANTS)

    # 보직 교수
    print("\n  [보직 교수]")
    print("  " + "─" * 45)
    for part, name in ROLE_PARTICIPANTS.items():
        profile_path = PROFILES_DIR / f"{part}.npy"
        if profile_path.exists():
            enrolled_at = meta.get(part, {}).get("enrolled_at", "알 수 없음")[:10]
            print(f"  ✅ {part:<8} {name} 교수  (등록일: {enrolled_at})")
            enrolled_count += 1
        else:
            print(f"  ❌ {part:<8} {name} 교수  (미등록)")

    # 일반 교수
    print("\n  [일반 교수]")
    print("  " + "─" * 45)
    for name in GENERAL_PROFESSORS:
        profile_path = PROFILES_DIR / f"{name}.npy"
        if profile_path.exists():
            enrolled_at = meta.get(name, {}).get("enrolled_at", "알 수 없음")[:10]
            print(f"  ✅ {name} 교수  (등록일: {enrolled_at})")
            enrolled_count += 1
        else:
            print(f"  ❌ {name} 교수  (미등록)")

    print("\n  " + "─" * 45)
    print(f"  총 {enrolled_count}/{total}명 등록됨\n")


# ─────────────────────────────────────────────
# 2. 녹음
# ─────────────────────────────────────────────
def record_audio(output_path: str, duration: int | None = None) -> str:
    try:
        import sounddevice as sd
    except ImportError:
        print("❌ sounddevice가 설치되지 않았습니다: pip install sounddevice")
        sys.exit(1)

    print("\n🎙️  녹음을 시작합니다...")
    if duration:
        print(f"   {duration}초 동안 녹음합니다.")
    else:
        print("   녹음을 멈추려면 Enter를 누르세요.")

    frames = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                        dtype="int16", callback=callback):
        if duration:
            sd.sleep(duration * 1000)
        else:
            input()

    print("✅ 녹음 완료!")

    audio_data = np.concatenate(frames, axis=0)
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data.tobytes())

    print(f"   저장됨: {output_path}")
    return output_path


# ─────────────────────────────────────────────
# 3. 화자 인식 + 발언 구간 분리
# ─────────────────────────────────────────────
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


def diarize_and_identify(audio_path: str, profiles: dict) -> list[dict]:
    """
    오디오를 발언 구간으로 분리하고 각 구간의 화자를 식별합니다.
    반환: [{"speaker": "서경률(주임교수)", "start": 0.0, "end": 5.2, "wav": np.ndarray}, ...]
    """
    from resemblyzer import VoiceEncoder, preprocess_wav

    print("\n🔍 화자 인식 중...")

    encoder = get_encoder()
    wav_full = load_audio(audio_path)

    try:
        wav_full = preprocess_wav(wav_full, source_sr=SAMPLE_RATE)
    except Exception:
        pass

    # 슬라이딩 윈도우로 구간별 임베딩 계산
    window_sec  = 1.5   # 윈도우 크기 (초)
    step_sec    = 0.5   # 슬라이딩 간격 (초)
    window_size = int(window_sec * SAMPLE_RATE)
    step_size   = int(step_sec  * SAMPLE_RATE)

    total_samples = len(wav_full)
    window_labels = []   # (start_sec, end_sec, speaker_label)

    for start in range(0, total_samples - window_size, step_size):
        end   = start + window_size
        chunk = wav_full[start:end]

        emb = encoder.embed_utterance(chunk)

        # 등록된 화자 중 가장 유사한 사람 찾기
        best_part  = None
        best_score = -1.0
        for part, profile_emb in profiles.items():
            score = cosine_similarity(emb, profile_emb)
            if score > best_score:
                best_score = score
                best_part  = part

        if best_part and best_score >= SIMILARITY_THRESHOLD:
            name    = PARTICIPANTS[best_part]
            label   = f"{name}({best_part})"
        else:
            label   = "미확인"

        window_labels.append({
            "start":   start / SAMPLE_RATE,
            "end":     end   / SAMPLE_RATE,
            "speaker": label,
            "wav":     chunk,
        })

    # 연속된 같은 화자 구간을 병합
    if not window_labels:
        return []

    segments = []
    cur = window_labels[0].copy()

    for w in window_labels[1:]:
        if w["speaker"] == cur["speaker"]:
            cur["end"] = w["end"]
            cur["wav"] = np.concatenate([cur["wav"], w["wav"][int(step_size):]])
        else:
            segments.append(cur)
            cur = w.copy()
    segments.append(cur)

    # 너무 짧은 구간 (< 0.8초) 은 앞 구간에 합치기
    merged = []
    for seg in segments:
        dur = seg["end"] - seg["start"]
        if dur < 0.8 and merged:
            merged[-1]["end"] = seg["end"]
            merged[-1]["wav"] = np.concatenate([merged[-1]["wav"], seg["wav"]])
        else:
            merged.append(seg)

    print(f"   총 {len(merged)}개 발언 구간 감지됨")
    return merged


# ─────────────────────────────────────────────
# 4. Whisper STT (구간별)
# ─────────────────────────────────────────────
def transcribe_segments(segments: list[dict], tmp_dir: Path) -> str:
    """각 구간을 Whisper로 전사하고 발언자 표시된 텍스트를 반환합니다."""
    try:
        import whisper
    except ImportError:
        print("❌ whisper가 설치되지 않았습니다: pip install openai-whisper")
        sys.exit(1)

    print(f"\n📝 Whisper 모델 로딩 중 ({WHISPER_MODEL})...")
    model = whisper.load_model(WHISPER_MODEL)

    tmp_dir.mkdir(parents=True, exist_ok=True)
    lines = []

    for i, seg in enumerate(segments):
        # 임시 wav 파일로 저장
        tmp_wav = tmp_dir / f"seg_{i:04d}.wav"
        audio_int16 = (seg["wav"] * 32768).clip(-32768, 32767).astype(np.int16)
        with wave.open(str(tmp_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

        result = model.transcribe(str(tmp_wav), language="ko", verbose=False)
        text   = result["text"].strip()

        if text:
            start_str = f"{seg['start']:.1f}s"
            end_str   = f"{seg['end']:.1f}s"
            lines.append(f"[{seg['speaker']}] ({start_str}~{end_str}): {text}")

    # 임시 파일 삭제
    shutil.rmtree(str(tmp_dir), ignore_errors=True)

    print("✅ 전사 완료!")
    return "\n".join(lines)


def transcribe_full(audio_path: str) -> str:
    """화자 프로파일 없을 때 전체 오디오를 한 번에 전사합니다."""
    try:
        import whisper
    except ImportError:
        print("❌ whisper가 설치되지 않았습니다: pip install openai-whisper")
        sys.exit(1)

    print(f"\n📝 Whisper 모델 로딩 중 ({WHISPER_MODEL})... (화자 인식 없이 전사)")
    model  = whisper.load_model(WHISPER_MODEL)
    result = model.transcribe(audio_path, language="ko", verbose=False)
    print("✅ 전사 완료!")
    return result["text"].strip()


# ─────────────────────────────────────────────
# 5. 회의록 생성 프롬프트
# ─────────────────────────────────────────────
def participants_info() -> str:
    role_lines    = [f"  - {part} 담당: {name} 교수" for part, name in ROLE_PARTICIPANTS.items()]
    general_lines = [f"  - {name} 교수" for name in GENERAL_PROFESSORS]
    return (
        "[보직 교수]\n" + "\n".join(role_lines) +
        "\n[일반 교수]\n" + "\n".join(general_lines)
    )


def build_prompt(transcript: str, meeting_title: str, meeting_date: str,
                 speaker_identified: bool) -> str:

    speaker_note = (
        "각 발언은 [이름(파트)] (시작~끝) 형식으로 화자가 표시되어 있습니다. "
        "이를 최대한 활용하여 파트별 보고 내용과 발언을 정확히 귀속해주세요."
        if speaker_identified else
        "화자 인식이 적용되지 않아 전체 텍스트로 제공됩니다. "
        "문맥에서 발언자를 추정하여 회의록을 작성해주세요."
    )

    # 참석자 현황 표: 보직 교수는 파트 표시, 일반 교수는 "-"
    role_rows    = "\n".join(f"| {part} | {name} 교수 | - |"
                             for part, name in ROLE_PARTICIPANTS.items())
    general_rows = "\n".join(f"| - | {name} 교수 | - |"
                             for name in GENERAL_PROFESSORS)

    return f"""아래는 회의 음성을 텍스트로 변환한 내용입니다.
이 내용을 바탕으로 전문적인 회의록을 작성해주세요.

회의 제목: {meeting_title}
회의 날짜: {meeting_date}

[고정 참석자 명단]
{participants_info()}

[음성 변환 원문]
{speaker_note}

{transcript}

---

다음 형식으로 회의록을 작성해주세요.

# {meeting_title}
**날짜:** {meeting_date}
**작성자:** (총무 담당: 김태임 교수)

## 1. 참석자 현황

**보직 교수**

| 파트 | 이름 | 참석 |
|------|------|------|
{role_rows}

**일반 교수**

| 파트 | 이름 | 참석 |
|------|------|------|
{general_rows}

(원문에서 발언이 확인된 교수님은 ✅, 불분명하면 -로 표시)

## 2. 주요 안건
(회의에서 다룬 핵심 주제들을 번호 목록으로 정리)

## 3. 파트별 보고 및 논의 내용
(발언이 확인된 분만 포함. 보직 교수는 파트명을, 일반 교수는 이름을 명시할 것)

형식 예시:
### 총무 (김태임 교수)
- 보고/발언 내용 요약

### 김성수 교수
- 발언 내용 요약

## 4. 결정 사항
(회의에서 확정된 사항들을 번호 목록으로 정리. 결정 주체가 파악되면 명시)

## 5. Action Items (후속 조치)

| 담당자 | 내용 | 기한 |
|--------|------|------|
| (이름/파트) | (할 일) | (기한 또는 미정) |

## 6. 기타 / 다음 회의 예정
(기타 언급 사항, 다음 회의 일정 등)

---
*본 회의록은 AI에 의해 자동 생성되었습니다. 내용을 검토 후 활용해주세요.*
"""


# ─────────────────────────────────────────────
# 6. LLM 회의록 생성
# ─────────────────────────────────────────────
def generate_minutes_claude(prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        print("❌ anthropic이 설치되지 않았습니다: pip install anthropic")
        sys.exit(1)
    if not ANTHROPIC_API_KEY:
        print("❌ ANTHROPIC_API_KEY 환경변수를 설정해주세요.")
        sys.exit(1)

    client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    print("\n🤖 Claude가 회의록을 작성 중...")
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    print("✅ 회의록 생성 완료! (Claude)")
    return message.content[0].text


def generate_minutes_gemini(prompt: str) -> str:
    try:
        import google.generativeai as genai
    except ImportError:
        print("❌ google-generativeai가 설치되지 않았습니다: pip install google-generativeai")
        sys.exit(1)
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY 환경변수를 설정해주세요.")
        sys.exit(1)

    genai.configure(api_key=GEMINI_API_KEY)
    print("\n🔍 사용 가능한 Gemini 모델 조회 중...")

    available = [
        m.name.replace("models/", "")
        for m in genai.list_models()
        if "generateContent" in m.supported_generation_methods and "gemini" in m.name
    ]

    def model_priority(name: str) -> tuple:
        import re
        ver_match = re.search(r"gemini-(\d+\.\d+|\d+)", name)
        version   = float(ver_match.group(1)) if ver_match else 0.0
        is_pro    = 1 if "pro"   in name else 0
        is_flash  = 1 if "flash" in name else 0
        is_exp    = -1 if ("exp" in name or "preview" in name) else 0
        return (version, is_pro, is_flash, is_exp)

    available.sort(key=model_priority, reverse=True)
    selected = available[0] if available else "gemini-2.0-flash"
    print(f"   선택된 모델: {selected}")

    model    = genai.GenerativeModel(selected)
    print("\n🤖 Gemini가 회의록을 작성 중...")
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(max_output_tokens=4096)
    )
    print("✅ 회의록 생성 완료! (Gemini)")
    return response.text


# ─────────────────────────────────────────────
# 7. 파일 저장
# ─────────────────────────────────────────────
def save_output(minutes: str, transcript: str, output_dir: str, title: str):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    safe_title = title.replace(" ", "_").replace("/", "-")
    timestamp  = datetime.datetime.now().strftime("%Y%m%d_%H%M")

    minutes_path    = os.path.join(output_dir, f"{timestamp}_{safe_title}_회의록.md")
    transcript_path = os.path.join(output_dir, f"{timestamp}_{safe_title}_원문.txt")

    with open(minutes_path,    "w", encoding="utf-8") as f: f.write(minutes)
    with open(transcript_path, "w", encoding="utf-8") as f: f.write(transcript)

    print(f"\n📄 회의록 저장: {minutes_path}")
    print(f"📄 원문 저장:   {transcript_path}")
    return minutes_path


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────
def main():
    global WHISPER_MODEL

    parser = argparse.ArgumentParser(
        description="회의 녹음 + 화자 인식 + 자동 회의록 생성기",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command")

    # ── enroll: 목소리 등록 ──────────────────
    p_enroll = subparsers.add_parser("enroll", help="교수님 목소리를 등록합니다")
    p_enroll.add_argument("--part", "-p", required=True,
        help=f"파트명. 선택 가능: {', '.join(PARTICIPANTS.keys())}")
    p_enroll.add_argument("--file", "-f", default=None,
        help="목소리 샘플 파일 (생략하면 마이크로 직접 녹음, 10~30초 권장)")
    p_enroll.add_argument("--duration", "-d", type=int, default=20,
        help="마이크 녹음 시간(초), 기본값: 20초")

    # ── list: 등록 현황 ──────────────────────
    subparsers.add_parser("list", help="등록된 화자 목록을 확인합니다")

    # ── run: 회의 진행 ───────────────────────
    p_run = subparsers.add_parser("run", help="회의를 녹음하고 회의록을 생성합니다")
    p_run.add_argument("--file", "-f", default=None,
        help="기존 오디오 파일 경로 (생략하면 마이크 녹음)")
    p_run.add_argument("--duration", "-d", type=int, default=None,
        help="녹음 시간(초). 생략하면 Enter를 누를 때까지 녹음")
    p_run.add_argument("--title", "-t", default="교수회의",
        help="회의 제목 (기본값: '교수회의')")
    p_run.add_argument("--output", "-o", default="./output",
        help="결과 저장 폴더 (기본값: ./output)")
    p_run.add_argument("--api", "-a", default="claude",
        choices=["claude", "gemini"],
        help="회의록 생성 API (기본값: claude)")
    p_run.add_argument("--whisper-model", "-w", default=WHISPER_MODEL,
        choices=["tiny", "base", "small", "medium", "large"],
        help=f"Whisper 모델 크기 (기본값: {WHISPER_MODEL})")
    p_run.add_argument("--no-speaker-id", action="store_true",
        help="화자 인식 없이 전체 텍스트로만 처리합니다")
    p_run.add_argument("--transcript-only", action="store_true",
        help="텍스트 변환만 하고 회의록은 생성하지 않습니다")

    args = parser.parse_args()

    # 서브커맨드 없으면 도움말 출력
    if not args.command:
        parser.print_help()
        return

    # ── enroll ──────────────────────────────
    if args.command == "enroll":
        if args.file:
            audio_path = args.file
        else:
            tmp_path = str(PROFILES_DIR / f"tmp_{args.part}.wav")
            PROFILES_DIR.mkdir(parents=True, exist_ok=True)
            print(f"\n[{args.part}] {PARTICIPANTS.get(args.part, '')} 교수 목소리를 {args.duration}초 동안 녹음합니다.")
            print("평소 회의에서 말씀하시듯 자연스럽게 이야기해주세요.")
            record_audio(tmp_path, args.duration)
            audio_path = tmp_path
        enroll_speaker(args.part, audio_path)
        return

    # ── list ────────────────────────────────
    if args.command == "list":
        list_enrolled()
        return

    # ── run ─────────────────────────────────
    if args.command == "run":
        WHISPER_MODEL = args.whisper_model
        meeting_date  = datetime.datetime.now().strftime("%Y년 %m월 %d일")
        timestamp     = datetime.datetime.now().strftime("%Y%m%d_%H%M")

        print("=" * 55)
        print(f"  🗒️  자동 회의록 생성기  [{args.api.upper()}]")
        print("=" * 55)

        # Step 1: 오디오 준비
        if args.file:
            audio_path = args.file
            if not os.path.exists(audio_path):
                print(f"❌ 파일을 찾을 수 없습니다: {audio_path}")
                sys.exit(1)
            print(f"📂 입력 파일: {audio_path}")
        else:
            Path(args.output).mkdir(parents=True, exist_ok=True)
            audio_path = os.path.join(args.output, f"{timestamp}_recording.wav")
            record_audio(audio_path, args.duration)

        # Step 2: 화자 인식 + 전사
        profiles = load_profiles() if not args.no_speaker_id else {}

        if profiles and not args.no_speaker_id:
            print(f"\n👤 화자 인식 모드: {len(profiles)}명 프로파일 로드됨")
            try:
                segments   = diarize_and_identify(audio_path, profiles)
                tmp_dir    = Path(args.output) / "tmp_segments"
                transcript = transcribe_segments(segments, tmp_dir)
                speaker_identified = True
            except Exception as e:
                print(f"⚠️  화자 인식 중 오류 발생: {e}")
                print("   화자 인식 없이 전체 텍스트로 전환합니다.")
                transcript = transcribe_full(audio_path)
                speaker_identified = False
        else:
            if not args.no_speaker_id:
                print("\n⚠️  등록된 화자 프로파일이 없습니다. 화자 인식 없이 진행합니다.")
                print("   먼저 'python meeting_minutes.py enroll --part 파트명' 으로 목소리를 등록하세요.")
            transcript = transcribe_full(audio_path)
            speaker_identified = False

        print("\n--- 변환된 텍스트 미리보기 ---")
        print(transcript[:400] + ("..." if len(transcript) > 400 else ""))
        print("------------------------------")

        if args.transcript_only:
            Path(args.output).mkdir(parents=True, exist_ok=True)
            safe_title      = args.title.replace(" ", "_")
            transcript_path = os.path.join(args.output, f"{timestamp}_{safe_title}_원문.txt")
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcript)
            print(f"\n📄 원문 저장: {transcript_path}")
            return

        # Step 3: 회의록 생성
        prompt = build_prompt(transcript, args.title, meeting_date, speaker_identified)
        if args.api == "gemini":
            minutes = generate_minutes_gemini(prompt)
        else:
            minutes = generate_minutes_claude(prompt)

        # Step 4: 저장
        save_output(minutes, transcript, args.output, args.title)

        print("\n" + "=" * 55)
        print("  ✅ 완료!")
        print("=" * 55)
        print("\n[회의록 미리보기]")
        print(minutes[:600] + ("..." if len(minutes) > 600 else ""))


if __name__ == "__main__":
    main()
