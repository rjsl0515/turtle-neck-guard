# TurtleNeckGuard (거북목 화면 교정기 - Windows 전용)

웹캠 기반 실시간 온디바이스 거북목 감지 및 화면 잠금 교정 프로그램입니다.  
모든 영상 프레임은 외부 서버로 전송되지 않고 로컬 메모리에서 즉시 처리·폐기됩니다.

## 주요 기능

- **실시간 거북목 감지 및 전체 화면 입력 차단 경고**: [Google MediaPipe Pose](https://github.com/google-ai-edge/mediapipe) 랜드마크를 기반으로 눈 간격 및 코–어깨 비율을 분석해 거북목 상태가 설정 시간 이상 지속되면 전체 화면 경고창을 띄웁니다. 바른 자세로 돌아오면 자동으로 잠금이 해제됩니다.
- **3초 분산 기반 자동 보정 & 원클릭 재보정**: 초기 3초 측정 시 자세 흔들림(분산)을 반영해 개인별 여유폭을 자동 보정하며, 버튼 한 번으로 현재 자세를 기준값으로 즉시 재학습할 수 있습니다.
- **회의 자동 매너 모드**: Zoom, Discord, Microsoft Teams, FaceTime, Webex 등 화상회의 앱 실행 중에는 화면 잠금을 자동으로 유예합니다.
- **7일 자세 통계 & 다국어·알람 설정**: 최근 7일 바른 자세 유지율 그래프, 오늘 감지 이력, 한국어/영어/일본어 전환, 누적 경고 알람 및 발표용 1분 시연 모드를 지원합니다.

## 폴더 구조

```text
turtle-neck-guard/
├── .github/workflows/
│   └── build-windows.yml      # GitHub 푸시 시 Windows 단일 .exe 자동 빌드
└── windows_package/           # Windows 실행·빌드 패키지
    ├── windows_app.py         # Windows 앱 진입점 (pywebview)
    ├── index.html             # Windows UI 및 MediaPipe Pose 분석 로직
    ├── build_exe.bat          # 로컬 PyInstaller 단일 .exe 빌드 스크립트
    ├── exe빌드.bat            # 로컬 PyInstaller 단일 .exe 빌드 스크립트 (한글명)
    └── README.txt             # Windows 실행 안내
```

## 실행 방법

### Windows (설치 없이 바로 실행)
1. GitHub 저장소 우측 **Releases** 페이지에서 **`거북목교정기.exe`** 파일을 다운로드합니다.
2. Python이나 가상환경 설치 없이 **`거북목교정기.exe`**를 더블클릭하면 바로 실행됩니다.

## 활용 오픈소스

- [Google MediaPipe](https://github.com/google-ai-edge/mediapipe) (Apache-2.0)
- [pywebview](https://github.com/r0x0r/pywebview) (BSD-3-Clause)
