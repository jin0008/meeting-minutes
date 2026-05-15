# 자동 회의록 생성기

OpenAI Whisper로 회의 음성을 텍스트로 변환하고, Claude 또는 Gemini API로 회의록을 자동 작성하는 도구입니다. 한국어 최적화, macOS · Windows 지원.

---

## 파일 구성

| 파일 | 설명 |
|------|------|
| `meeting.py` | 화자 구분 없이 전체 텍스트 변환 후 회의록 생성 |
| `meeting_voice.py` | 사전 등록된 목소리로 발언자를 식별해 회의록 생성 |

---

## 요구사항

- Python 3.10 이상
- macOS 12+ 또는 Windows 10/11
- 여유 디스크 공간 약 2GB (Whisper medium 모델)

---

## 설치

### 1. 저장소 클론

```bash
git clone https://github.com/jin0008/meeting-minutes.git
cd meeting-minutes
```

### 2. 패키지 설치

**macOS**
```bash
pip3 install -r requirements.txt
```

SSL 오류가 발생하면 아래를 먼저 실행하세요 (python.org 설치 버전 한정):
```bash
/Applications/Python\ 3.12/Install\ Certificates.command
```

**Windows** (PowerShell 관리자 권한)
```powershell
pip install -r requirements.txt
```

`webrtcvad` 설치 오류 시:
```powershell
pip install webrtcvad-wheels
pip install -r requirements.txt
```

mp3 파일을 사용하려면 FFmpeg도 필요합니다:
```powershell
winget install ffmpeg
```

> Windows에서 `resemblyzer` 설치에는 [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)가 필요합니다. 설치 시 "C++를 사용한 데스크톱 개발"을 선택하세요.

### 3. API 키 설정

Claude ([발급](https://console.anthropic.com/)) 또는 Gemini ([발급](https://aistudio.google.com/app/apikey), 무료 티어 있음) 중 하나를 사용합니다.

**macOS**
```bash
export ANTHROPIC_API_KEY="sk-..."
export GEMINI_API_KEY="AIza..."

# 영구 적용하려면 ~/.zshrc에 위 두 줄을 추가하세요
```

**Windows (PowerShell)**
```powershell
# 현재 세션
$env:ANTHROPIC_API_KEY = "sk-..."
$env:GEMINI_API_KEY = "AIza..."

# 영구 적용
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-...", "User")
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "AIza...", "User")
```

또는 **설정 → 시스템 → 정보 → 고급 시스템 설정 → 환경 변수**에서 직접 추가할 수 있습니다.

### 4. 마이크 권한

- **macOS**: 시스템 설정 → 개인 정보 보호 및 보안 → 마이크 → 사용 중인 터미널 앱 허용
- **Windows**: 설정 → 개인 정보 및 보안 → 마이크 → 앱 액세스 허용

---

## 사용법

> macOS는 `python3`, Windows는 `python` 명령어를 사용합니다. 이하 예시는 `python` 기준입니다.

### meeting.py — 기본 버전

```bash
# 마이크 녹음 (Enter로 종료)
python meeting.py run --title "5월 교수회의" --api gemini

# 녹음 시간 지정 (초)
python meeting.py run --title "주간 회의" --duration 60 --api claude

# 기존 녹음 파일 사용
python meeting.py run --file recording.mp3 --title "월례회의" --api gemini

# 텍스트 변환만 수행
python meeting.py run --file recording.wav --transcript-only
```

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--file`, `-f` | 오디오 파일 경로 | 마이크 녹음 |
| `--title`, `-t` | 회의 제목 | `교수회의` |
| `--duration`, `-d` | 녹음 시간 (초) | Enter 누를 때까지 |
| `--output`, `-o` | 결과 저장 폴더 | `./output` |
| `--api`, `-a` | `claude` 또는 `gemini` | `claude` |
| `--whisper-model`, `-w` | Whisper 모델 크기 | `medium` |
| `--transcript-only` | 텍스트 변환만 수행 | — |

---

### meeting_voice.py — 화자 인식 버전

목소리를 미리 등록해두면 발언자를 자동으로 식별합니다. 프로파일은 한 번 등록하면 영구 저장됩니다.

- **macOS**: `~/.meeting_minutes/speaker_profiles/`
- **Windows**: `C:\Users\사용자명\.meeting_minutes\speaker_profiles\`

#### 목소리 등록 (최초 1회)

```bash
# 마이크로 직접 녹음 (20초, 평소처럼 자연스럽게 말하면 됩니다)
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

# 기존 음성 파일로 등록
python meeting_voice.py enroll --part 주임교수 --file voice_sample.wav

# 녹음 시간 변경 (기본 20초)
python meeting_voice.py enroll --part 병원장 --duration 30
```

#### 등록 현황 확인

```bash
python meeting_voice.py list
```

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

#### 회의 진행

```bash
# 마이크 녹음 + 화자 인식
python meeting_voice.py run --title "5월 교수회의" --api gemini

# 기존 파일 사용
python meeting_voice.py run --file meeting.mp3 --title "월례회의" --api claude

# 화자 인식 없이 실행
python meeting_voice.py run --title "회의" --api gemini --no-speaker-id
```

화자 인식이 적용된 원문 예시:
```
[서경률(주임교수)] (0.0s~12.3s): 오늘 안건은 수련 일정 관련해서 논의하겠습니다.
[김태임(총무)] (12.5s~25.1s): 이번 달 예산 보고 드리겠습니다.
[미확인] (25.2s~27.0s): 네, 알겠습니다.
```

---

## 출력 결과

회의 종료 후 `./output/` 폴더에 두 파일이 생성됩니다.

```
output/
├── 20260514_1400_5월교수회의_회의록.md   ← AI가 작성한 회의록
└── 20260514_1400_5월교수회의_원문.txt    ← 음성 변환 원문
```

회의록은 다음 항목으로 구성됩니다.

1. 참석자 현황 (보직 교수 / 일반 교수)
2. 주요 안건
3. 파트별 보고 및 논의 내용
4. 결정 사항
5. Action Items
6. 기타 / 다음 회의 예정

---

## Whisper 모델

| 모델 | 크기 | 한국어 정확도 | 비고 |
|------|------|--------------|------|
| `tiny` | 75MB | 낮음 | 테스트용 |
| `base` | 145MB | 보통 | — |
| `small` | 460MB | 좋음 | — |
| `medium` | 1.5GB | 매우 좋음 | 기본값 |
| `large` | 3GB | 최고 | 고정밀 필요 시 |

모델은 최초 실행 시 자동으로 다운로드됩니다.

---

## 트러블슈팅

**webrtcvad 설치 오류 (Windows)**  
Microsoft C++ Build Tools가 없는 경우 발생합니다. `pip install webrtcvad-wheels`로 대체하거나 Build Tools를 설치하세요.

**mp3 파일 인식 불가 (Windows)**  
FFmpeg가 설치되어 있지 않은 경우입니다. `winget install ffmpeg` 실행 후 터미널을 재시작하세요.

**마이크 인식 불가**  
OS 마이크 권한을 확인하세요. 권한 변경 후에는 터미널을 재시작해야 적용됩니다.

**화자 인식 정확도가 낮음**  
조용한 환경에서 30초 이상 등록하면 정확도가 높아집니다. 회의 녹음과 유사한 마이크 환경에서 등록하는 것이 좋습니다.

**Gemini 모델 오류**  
스크립트가 사용 가능한 모델을 자동으로 조회합니다. API 키가 올바르게 설정되어 있는지 확인하세요.

---

## 라이선스

MIT
