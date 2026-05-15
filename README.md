# 🗒️ AI 자동 회의록 생성기

> OpenAI Whisper + Claude / Gemini API를 활용한 한국어 회의 녹음 및 자동 회의록 작성 도구  
> **macOS · Windows 지원**

---

## 📋 프로젝트 개요

이 프로젝트는 병원 교수 회의를 위한 **자동 회의록 생성 시스템**입니다.  
회의 중 음성을 녹음하거나 기존 녹음 파일을 입력하면, AI가 자동으로 한국어 텍스트로 변환하고 전문적인 회의록 문서를 생성합니다.

### 파일 구성

| 파일 | 설명 |
|------|------|
| `meeting.py` | 기본 버전 — 화자 구분 없이 전체 텍스트 변환 후 회의록 생성 |
| `meeting_voice.py` | 고급 버전 — 사전 등록된 목소리로 발언자를 자동 식별하여 회의록 생성 |

---

## ✨ 주요 기능

- 🎙️ **실시간 마이크 녹음** 또는 **기존 오디오 파일** (mp3, wav, m4a 등) 입력
- 📝 **OpenAI Whisper** 기반 고정밀 한국어 음성→텍스트 변환 (로컬 실행, 무료)
- 👤 **화자 인식** (`meeting_voice.py`): 교수님별 목소리를 사전 등록해 발언자 자동 식별
- 🤖 **Claude 또는 Gemini API** 선택 가능 (`--api claude` / `--api gemini`)
- 📄 결과물: **회의록 (.md)** + **원문 텍스트 (.txt)** 자동 저장
- 👥 고정 참석자(보직/일반 교수) 명단 자동 포함

---

## 🖥️ 시스템 요구사항

| 항목 | 요구사항 |
|------|----------|
| Python | **3.10 이상** |
| OS | macOS 12+, Windows 10/11 |
| 인터넷 | API 호출 및 Whisper 모델 최초 다운로드 시 필요 |
| 여유 용량 | Whisper medium 모델 기준 약 2GB |

---

## 📦 설치 방법

### 1. Python 설치

<details>
<summary>🍎 macOS</summary>

[python.org](https://www.python.org/downloads/)에서 Python 3.12 다운로드 후 설치합니다.  
설치 후 터미널에서 확인:
```bash
python3 --version
```

</details>

<details>
<summary>🪟 Windows</summary>

1. [python.org](https://www.python.org/downloads/)에서 Python 3.12 다운로드
2. 설치 시 **"Add Python to PATH"** 체크박스를 반드시 선택
3. PowerShell(관리자)에서 확인:
```powershell
python --version
```

> **Windows에서 resemblyzer 설치 전 필수 작업**  
> [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) 를 설치해야 합니다.  
> 설치 시 "C++를 사용한 데스크톱 개발" 항목을 선택하세요.

</details>

---

### 2. 저장소 클론

```bash
git clone https://github.com/jin0008/meeting-minutes.git
cd meeting-minutes
```

---

### 3. Python 패키지 설치

<details>
<summary>🍎 macOS</summary>

```bash
pip3 install -r requirements.txt
```

**SSL 오류 발생 시** (python.org에서 Python 설치한 경우):
```bash
/Applications/Python\ 3.12/Install\ Certificates.command
```

</details>

<details>
<summary>🪟 Windows</summary>

PowerShell을 **관리자 권한**으로 열고 실행:

```powershell
pip install -r requirements.txt
```

**webrtcvad 설치 오류 발생 시** (resemblyzer 의존 패키지):
```powershell
pip install webrtcvad-wheels
pip install -r requirements.txt
```

**mp3 파일 사용 시 FFmpeg 필요:**
1. [ffmpeg.org](https://ffmpeg.org/download.html) 또는 winget으로 설치:
```powershell
winget install ffmpeg
```
2. 설치 후 PowerShell 재시작

</details>

---

### 4. API 키 설정

**Claude API** ([발급 링크](https://console.anthropic.com/)):

<details>
<summary>🍎 macOS</summary>

```bash
# 현재 세션에만 적용
export ANTHROPIC_API_KEY="your-api-key-here"

# 영구 적용 (~/.zshrc에 추가)
echo 'export ANTHROPIC_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

</details>

<details>
<summary>🪟 Windows</summary>

```powershell
# 현재 세션에만 적용 (PowerShell)
$env:ANTHROPIC_API_KEY = "your-api-key-here"

# 영구 적용 (재부팅 없이 유지)
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "your-api-key-here", "User")
```

또는 GUI로 설정:  
**Windows 검색 → "환경 변수" → 사용자 변수 → 새로 만들기**  
변수 이름: `ANTHROPIC_API_KEY` / 변수 값: 발급받은 키

</details>

**Gemini API** ([발급 링크](https://aistudio.google.com/app/apikey) — 무료 티어 제공):

<details>
<summary>🍎 macOS</summary>

```bash
export GEMINI_API_KEY="your-api-key-here"

# 영구 적용
echo 'export GEMINI_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

</details>

<details>
<summary>🪟 Windows</summary>

```powershell
$env:GEMINI_API_KEY = "your-api-key-here"

# 영구 적용
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your-api-key-here", "User")
```

</details>

---

### 5. 마이크 권한 설정 (직접 녹음 시)

<details>
<summary>🍎 macOS</summary>

**시스템 설정 → 개인 정보 보호 및 보안 → 마이크**  
사용하는 터미널 앱(Terminal, iTerm2 등)을 허용합니다.

</details>

<details>
<summary>🪟 Windows</summary>

**설정 → 개인 정보 및 보안 → 마이크**  
"앱이 마이크에 액세스하도록 허용"을 켠 다음 목록에서 PowerShell / Windows Terminal을 허용합니다.

</details>

---

## 🚀 사용 방법

> **macOS**: `python3` 명령어 사용  
> **Windows**: `python` 명령어 사용  
> 아래 예시는 `python` 기준으로 작성되어 있습니다.

---

### `meeting.py` — 기본 버전 (화자 구분 없음)

```bash
# 마이크로 직접 녹음 (Enter를 누르면 녹음 종료)
python meeting.py run --title "5월 교수회의" --api gemini

# 시간 지정 녹음 (60초)
python meeting.py run --title "주간 회의" --duration 60 --api claude

# 기존 녹음 파일 사용
python meeting.py run --file recording.mp3 --title "월례회의" --api gemini

# 텍스트 변환만 (회의록 생성 없음)
python meeting.py run --file recording.wav --transcript-only
```

**옵션 설명:**

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--file`, `-f` | 오디오 파일 경로 | (마이크 녹음) |
| `--title`, `-t` | 회의 제목 | `교수회의` |
| `--duration`, `-d` | 녹음 시간(초) | Enter 누를 때까지 |
| `--output`, `-o` | 결과 저장 폴더 | `./output` |
| `--api`, `-a` | LLM API 선택 (`claude` / `gemini`) | `claude` |
| `--whisper-model`, `-w` | Whisper 모델 크기 | `medium` |
| `--transcript-only` | 텍스트 변환만 수행 | — |

---

### `meeting_voice.py` — 고급 버전 (화자 인식)

#### Step 1. 목소리 등록 (최초 1회)

등록된 프로파일은 아래 경로에 영구 저장됩니다.
- **macOS**: `~/.meeting_minutes/speaker_profiles/`
- **Windows**: `C:\Users\사용자명\.meeting_minutes\speaker_profiles\`

```bash
# 마이크로 직접 녹음 (20초간 자연스럽게 말씀하시면 됩니다)
python meeting_voice.py enroll --part 주임교수
python meeting_voice.py enroll --part 병원장
python meeting_voice.py enroll --part 총무
python meeting_voice.py enroll --part 부총무
python meeting_voice.py enroll --part 수련
python meeting_voice.py enroll --part 학생
python meeting_voice.py enroll --part 연구
python meeting_voice.py enroll --part 수술실
python meeting_voice.py enroll --part 외래
python meeting_voice.py enroll --part 인재개발
python meeting_voice.py enroll --part 세목회

# 일반 교수는 이름으로 등록
python meeting_voice.py enroll --part 김성수
python meeting_voice.py enroll --part 변석호
python meeting_voice.py enroll --part 배형원
python meeting_voice.py enroll --part 한재용
python meeting_voice.py enroll --part 곽지용
python meeting_voice.py enroll --part 김진영
python meeting_voice.py enroll --part 조진

# 기존 녹음 파일로 등록
python meeting_voice.py enroll --part 주임교수 --file seo_voice.wav

# 녹음 시간 지정 (기본 20초)
python meeting_voice.py enroll --part 병원장 --duration 30
```

#### Step 2. 등록 현황 확인

```bash
python meeting_voice.py list
```

출력 예시:
```
  [보직 교수]
  ─────────────────────────────────────────────
  ✅ 주임교수   서경률 교수  (등록일: 2026-05-14)
  ✅ 병원장     김찬윤 교수  (등록일: 2026-05-14)
  ❌ 총무       김태임 교수  (미등록)

  [일반 교수]
  ─────────────────────────────────────────────
  ✅ 김성수 교수  (등록일: 2026-05-14)
  ❌ 변석호 교수  (미등록)
```

#### Step 3. 회의 진행

```bash
# 마이크 녹음 + 화자 인식 + 회의록 생성
python meeting_voice.py run --title "5월 교수회의" --api gemini

# 기존 파일 사용
python meeting_voice.py run --file meeting.mp3 --title "월례회의" --api claude

# 화자 인식 없이 실행
python meeting_voice.py run --title "회의" --api gemini --no-speaker-id
```

**화자 인식 결과 원문 예시:**
```
[서경률(주임교수)] (0.0s~12.3s): 오늘 안건은 수련 일정 관련해서 논의하겠습니다.
[김태임(총무)] (12.5s~25.1s): 이번 달 예산 보고 드리겠습니다.
[미확인] (25.2s~27.0s): 네, 알겠습니다.
```

---

## 📄 출력 결과물

`./output/` 폴더에 다음 두 파일이 저장됩니다:

- `YYYYMMDD_HHMM_회의제목_회의록.md` — AI가 작성한 최종 회의록
- `YYYYMMDD_HHMM_회의제목_원문.txt` — 음성 변환 원문 텍스트

**회의록 구성:**
1. 참석자 현황 (보직 교수 / 일반 교수)
2. 주요 안건
3. 파트별 보고 및 논의 내용
4. 결정 사항
5. Action Items (담당자 / 내용 / 기한)
6. 기타 / 다음 회의 예정

---

## ⚙️ Whisper 모델 선택 가이드

| 모델 | 크기 | 속도 | 한국어 정확도 | 권장 |
|------|------|------|--------------|------|
| `tiny` | 75MB | 매우 빠름 | 낮음 | 테스트용 |
| `base` | 145MB | 빠름 | 보통 | — |
| `small` | 460MB | 보통 | 좋음 | — |
| `medium` | 1.5GB | 느림 | 매우 좋음 | ✅ 기본값 |
| `large` | 3GB | 매우 느림 | 최고 | 고정밀 필요 시 |

> Whisper 모델은 **최초 실행 시 자동 다운로드**됩니다.

---

## 🔧 요구 패키지 (`requirements.txt`)

```
sounddevice         # 마이크 녹음
openai-whisper      # 음성→텍스트 (STT)
resemblyzer         # 화자 인식 (meeting_voice.py 전용)
librosa             # 오디오 처리
numpy               # 수치 연산
anthropic           # Claude API (선택)
google-generativeai # Gemini API (선택)
```

---

## ❓ 자주 묻는 문제

**Q. macOS에서 SSL 인증서 오류가 발생해요.**  
A. 아래 명령어를 실행하세요:
```bash
/Applications/Python\ 3.12/Install\ Certificates.command
```

**Q. Windows에서 `webrtcvad` 설치 오류가 나요.**  
A. Microsoft C++ Build Tools를 먼저 설치하거나, 아래 명령어로 미리 빌드된 버전을 설치하세요:
```powershell
pip install webrtcvad-wheels
```

**Q. Windows에서 mp3 파일을 인식 못해요.**  
A. FFmpeg 설치가 필요합니다:
```powershell
winget install ffmpeg
```

**Q. 마이크가 인식되지 않아요.**  
A. OS별 마이크 권한을 확인해주세요.  
- macOS: 시스템 설정 → 개인 정보 보호 및 보안 → 마이크  
- Windows: 설정 → 개인 정보 및 보안 → 마이크

**Q. Whisper 모델 다운로드가 너무 오래 걸려요.**  
A. `--whisper-model small`로 더 작은 모델을 사용하거나, 최초 1회 다운로드 후에는 빠르게 실행됩니다.

**Q. 화자 인식 정확도를 높이려면?**  
A. 조용한 환경에서 20~30초간 자연스러운 말투로 등록해주세요.

**Q. Gemini 모델을 찾을 수 없다는 오류가 나요.**  
A. GEMINI_API_KEY가 올바르게 설정되어 있는지 확인해주세요. 스크립트가 사용 가능한 최신 모델을 자동 조회합니다.

---

## 📁 디렉토리 구조

```
meeting-minutes/
├── meeting.py              # 기본 버전 (화자 구분 없음)
├── meeting_voice.py        # 고급 버전 (화자 인식)
├── requirements.txt        # 필수 패키지 목록
├── README.md               # 이 문서
└── output/                 # 생성된 회의록 저장 폴더 (자동 생성)
    ├── 20260514_1400_교수회의_회의록.md
    └── 20260514_1400_교수회의_원문.txt
```

---

## 📝 라이선스

MIT License

---

*본 프로젝트는 병원 교수 회의의 효율적인 기록을 위해 제작되었습니다.*
