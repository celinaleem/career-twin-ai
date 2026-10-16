# Career Twin AI

개인 경험의 근거를 찾고, 합성 채용 사례와 역량을 비교하며, 논문으로 면접을 준비하는 개인용 RAG 웹 앱입니다. Colab 임시 공유 링크 대신 **VS Code + Python 모듈 + Streamlit + Ollama** 구조로 구현했습니다.

## 구현한 기능

- **내 자료:** PDF·Markdown·TXT 업로드, 페이지·섹션 단위 청킹, 원문 보기, 지속 저장 및 삭제.
- **공고 탐색:** 사람인 공식 채용정보 API에서 실제 공고를 가져와 개인 문서 내용과 가까운 순서로 정렬. API 키가 없을 때는 Resume Matching Dataset v2의 합성 공고로 시연.
- **이력서·공고 비교:** 저장된 개인 문서 한 개 또는 붙여넣은 이력서와 JD를 나란히 비교. 요구사항별 관련 원문, 이력서에 없는 영문 기술 키워드, 사실에 맞게 문장을 보완하는 제안을 표시하고 Markdown으로 저장.
- **경험 질문:** 개인 문서만 검색해 원문과 출처 표시. Ollama 모드에서는 근거 기반 답변 생성.
- **JD 근거 매칭:** 공고의 요구사항 추출 → 사용자 편집·삭제 → 항목별 경험 검색 → 직접 근거/관련 경험/근거 없음 판정.
- **논문·면접 준비:** 논문 PDF 본문 검색, 페이지 이미지 렌더링, 선택적으로 VLM으로 아키텍처 설명·면접 연습 질문 생성.
- **검증:** 개인 답변·매칭의 청크 ID와 원문 인용 일치 확인. 검증에 실패한 주장은 제외하거나 근거 없음으로 처리.

모델 학습·파인튜닝은 하지 않습니다. 일반 모드의 검색은 BM25이며, 의미 검색 옵션을 켜면 Ollama 임베딩과 FAISS 검색을 RRF로 합칩니다. 원문 인용 검증은 문장의 의미적 타당성까지 보장하지 않습니다. 논문 VLM 답변은 생성된 결과이므로 출처·그림 해석을 직접 확인해야 합니다.

## 데이터와 모델

| 용도 | 구성 |
| --- | --- |
| 공개 실험 데이터 | `jminc/resume-matching-dataset-v2` |
| 텍스트 답변 | Ollama `qwen2.5:3b` |
| 의미 검색 | Ollama `embeddinggemma` + FAISS |
| 그림 설명 | Ollama `qwen2.5vl:3b` |
| 화면 | Streamlit |
| 개인 자료 저장 | SQLite + 원본 파일 |

실제 공고 추천은 사람인 공식 API 키가 있을 때 동작합니다. 공개 데이터는 모두 합성 사례이며 실제 모집 중 공고·합격자 지원서·합격 확률이 아닙니다. 생성 평가문·점수는 공고 검색 입력에 포함하지 않으며, 합성 지원자의 경험을 개인 경험 DB에 저장하지 않습니다. 데이터 카드에 명시된 교육·연구 목적과 출처 표기를 따릅니다.

## 폴더 구성

```text
career-twin-ai/
├── app.py                       # 웹 화면과 사용자 동작
├── career_twin/
│   ├── config.py                # 경로·모델 설정
│   ├── ingest.py                # 파일 추출·청킹·PDF 페이지 렌더링
│   ├── storage.py               # 문서·청크·임베딩 저장과 삭제
│   ├── retrieval.py             # BM25·임베딩·FAISS 검색
│   ├── compare.py               # 이력서 문장·JD 비교와 키워드 확인
│   ├── local_ai.py              # Ollama API 호출
│   ├── services.py              # 요구사항 추출·검증·매칭·논문 답변
│   └── dataset.py               # 공개 실험 데이터 로딩
├── scripts/prepare_dataset.py   # 실제 HF 데이터 소량 다운로드
├── tests/test_core.py           # 근거·자료 분리·삭제 테스트
├── examples/                    # 사람이 작성한 시연 문서 (실제 경력 아님)
├── requirements.txt             # 앱 의존성
├── requirements-data.txt        # 다운로드 도구 의존성
├── Dockerfile / compose.yaml    # 단일 작업 공간 컨테이너 구성
└── data/                        # 실행 후 생성. Git·Docker 빌드에서 제외
```

이 저장소에는 개인 업로드, SQLite DB, 다운로드된 합성 데이터, `.env`, 가상환경을 포함하지 않습니다. 각자 로컬에서 데이터 준비 명령을 실행하세요. 기존 폴더를 GitHub에 올릴 때는 `data/private/`를 포함하지 않도록 특히 주의하세요.


## VS Code에서 실행

Python 3.11 또는 3.12를 권장합니다. **VS Code에서 이 `career-twin-ai` 폴더 자체를 열고** 터미널을 실행하세요.

### Mac / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-data.txt
python scripts/prepare_dataset.py --limit 300
python -m streamlit run app.py
```

### Windows PowerShell

활성화 명령 없이 가상환경의 Python을 직접 사용하면 실행 정책 문제를 피할 수 있습니다.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-data.txt
.\.venv\Scripts\python.exe scripts\prepare_dataset.py --limit 300
.\.venv\Scripts\python.exe -m streamlit run app.py
```

브라우저에서 `http://localhost:8501`을 엽니다. Colab과 달리 Python 프로세스가 실행 중인 동안 본인 컴퓨터에서 접속합니다. VS Code의 Python 인터프리터를 `.venv`로 선택하면 F5 실행 설정도 사용할 수 있습니다.

### 실제 채용공고 추천

사람인 채용정보 API access-key를 발급받은 뒤 앱 실행 전 환경변수로 설정합니다.

```powershell
$env:SARAMIN_ACCESS_KEY="발급받은_키"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

키가 없으면 실제 공고 호출은 실행되지 않고, 공고 탐색 탭의 데모용 합성 공고 검색만 사용할 수 있습니다. 잡코리아·원티드 등 다른 사이트는 공식 API 또는 사용 허용 범위가 확인되면 같은 방식으로 소스를 추가할 수 있습니다.

API 키 없이 실험하려면 공고 탐색 탭에서 **잡코리아 검색 크롤링**을 선택하고 희망 직무·기술을 입력합니다. 앱이 잡코리아 검색 결과 페이지에서 공개 공고 목록을 읽어 내 경험 문서와 가까운 순서로 정렬합니다. 이 기능은 로그인, 봇 차단 우회, JavaScript 실행을 하지 않는 단순 HTML 추출입니다. 사이트에 따라 결과가 비어 있거나 실패할 수 있으며, 그때는 사람인 API 방식으로 돌아가거나 공고 본문을 직접 복사해 JD 근거 매칭 탭에 붙여넣어 분석합니다.

### 첫 시연

1. 내 자료 탭에 `examples/my_experience_demo.md`를 업로드합니다. 이것은 개발자가 작성한 예시이며 실제 본인 경력이 아닙니다.
2. 검색 전용 모드에서 BM25로 경험을 검색합니다. Ollama 임베딩 모델을 준비했다면 **의미 검색 + FAISS**도 켤 수 있습니다.
3. JD 탭에 `examples/jd_demo.txt`를 붙여 넣고 요구사항을 추출·편집합니다.
4. 이력서 비교 탭에서 등록한 예시 문서를 선택하거나 이력서 텍스트를 붙여넣고 같은 JD와 비교합니다. 문장 후보·빠진 영문 기술 키워드·수정 제안을 확인합니다.
5. 공고 탐색에서 `Python RAG FAISS`를 입력해 사람인 실제 공고를 찾습니다. API 키가 없다면 접혀 있는 데모용 합성 공고 탐색을 사용합니다.
6. 논문 PDF를 **논문·학술자료**로 업로드하고 관련 근거를 검색합니다.

검색 전용 모드에서는 원문 확인과 검색만 합니다. 근거 판정은 **판정 대기**로 표시하며, AI 답변을 실행한 것처럼 보여주지 않습니다.
이력서 비교의 "관련 표현 발견"은 검색 후보이며 수행 경험이나 채용 적합도 판정이 아닙니다. "경험 확인 필요"는 해당 문장에 미수행·학습 예정 같은 표현이 있는 경우입니다. 키워드의 부재도 역량의 부재를 뜻하지 않습니다.

## AI와 VLM 사용

[Ollama](https://ollama.com/)를 설치하고 다음 모델을 준비하세요. GPU가 없어도 가능하지만 CPU에서는 느릴 수 있습니다. 모델은 필요할 때 요청하며 각 요청 후 메모리 해제를 요청합니다.

```bash
ollama pull qwen2.5:3b
ollama pull embeddinggemma
ollama pull qwen2.5vl:3b
```

Ollama가 실행 중이지 않으면 별도 터미널에서 `ollama serve`를 실행합니다.

- AI 답변: 사이드바에서 **Ollama AI 답변** 선택.
- 의미 검색: **의미 검색 + FAISS** 선택. 문서 임베딩은 SQLite에 모델·청크별로 캐시합니다. FAISS 인덱스는 검색할 때 캐시 벡터로 재구성합니다.
- 그림 설명: 논문 검색 → PDF·페이지 선택 → **이 페이지 그림도 VLM으로 읽기** 선택 → 설명 버튼.
- 그림은 PDF 페이지를 이미지로 변환합니다. 그림만 자동 분리하거나 SigLIP으로 검색하는 기능은 현재 포함하지 않았습니다.
- 외부 논문을 자동으로 검색·다운로드하지 않습니다. 업로드된 논문 안에서 검색합니다.

모델은 `career_twin/config.py` 또는 환경변수 `CHAT_MODEL`, `EMBED_MODEL`, `VISION_MODEL`, `OLLAMA_URL`로 바꿀 수 있습니다. 로컬 실행은 `.env`를 자동 로딩하지 않습니다. `.env`는 Docker Compose용입니다.

## 데이터 준비와 재현

```bash
python scripts/prepare_dataset.py --limit 300 --role LLM --max-scan 5000
```

`--role`은 정확한 직무 라벨이 아닌 **공고 본문 키워드 필터**입니다. 결과가 적으면 필터를 빼거나 스캔 수를 늘리세요. 스트리밍으로 처음 만나는 일치 사례를 선택합니다. 무작위·대표 표본은 아닙니다.

`data/public/manifest.json`에 실제 다운로드 수, 필터, 스캔 수, 날짜, 파일 해시, 데이터셋 commit SHA를 기록합니다. 기존 300건 시연과 같은 데이터 revision을 사용하려면 다음처럼 실행합니다.

```bash
python scripts/prepare_dataset.py --limit 300 --revision 5400cbfef5254891e863732f5e00e67cc02a0cad
```

개인 원본·청크·임베딩은 `data/private/`에, 공개 사례는 `data/public/`에 별도로 저장합니다. 개인 문서 삭제 시 원본과 연결 청크·임베딩도 삭제합니다.

## 배포 경로

**현재 공개 배포하지 않았습니다.** 컨테이너에서 앱과 Ollama를 같이 실행하는 설정을 제공했습니다.

```bash
# .env.example을 .env로 복사하고 APP_PASSWORD를 본인 비밀번호로 변경
# Mac: cp .env.example .env
# PowerShell: Copy-Item .env.example .env
docker compose up --build -d
docker compose exec ollama ollama pull qwen2.5:3b
docker compose exec ollama ollama pull embeddinggemma
docker compose exec ollama ollama pull qwen2.5vl:3b
docker compose exec app python scripts/prepare_dataset.py --limit 300
```

이후 `http://localhost:8501`에 접속합니다. 기본 컨테이너 설정은 CPU 실행이며 GPU 설정은 포함하지 않았습니다. Docker 실행 자체는 아직 검증하지 않았습니다.

서버 배포도 같은 구조로 가능하지만 도메인·HTTPS·접근 제한과 서버 자원이 필요합니다. 제공한 로그인은 **단일 소유자의 공유 작업 공간 비밀번호**이며 다중 사용자별 저장소 분리 기능이 아닙니다. 컨테이너 볼륨에 원본 자료가 지속 저장되므로 공용 시연에는 예시 자료를 사용하세요. Streamlit Community Cloud에 화면만 올리면 `localhost`의 Ollama가 연결되는 것은 아니므로, AI 모델 서버도 별도로 준비해야 합니다.

## 팀 역할

- 담당 A: 개인 문서·데이터셋·공고 탐색·JD 추출·근거 매칭.
- 담당 B: 논문 전처리·본문 검색·페이지 이미지·VLM·면접 질문.
- 공동: 요구사항 전달 형식, 통합 화면, 직접 작성한 평가 사례와 발표.

## GitHub 공동 작업

처음에는 **비공개 저장소**로 공유하고, 팀원의 GitHub 계정을 공동 작업자로 초대하세요. 각자는 저장소를 clone해 자기 브랜치에서 작업하고 pull request로 변경을 합칩니다. `main`에는 검증된 변경만 넣는 편이 좋습니다. 이 저장소의 GitHub Actions는 Python 3.11·3.12에서 핵심 테스트를 실행합니다.

개인 업로드, `data/`, `.env`, 가상환경은 커밋하거나 pull request에 첨부하지 마세요. 팀원이 각각 자신의 로컬 문서를 등록하면 자료가 분리됩니다. 한 서버에 함께 접속하는 경우에는 현재 앱의 문서 저장소와 비밀번호를 **모든 사용자가 공유**하므로 개인 자료를 올리는 용도로 사용하지 마세요.

## 검증과 남은 작업

```bash
python -m unittest discover -s tests -v
```

2026-10-17 로컬 검증: **테스트 8개 통과**, Streamlit 브라우저에서 이력서 비교 입력·결과와 초기 화면·공고 탐색 탭 로딩 확인. 합성 사례 300개와 기존 작업 폴더 manifest SHA-256 일치를 확인했습니다. 데이터는 이 공유용 저장소에서 제외했습니다.

확인한 항목: 개인·논문 자료 분리, 재시작 후 저장, 중복 등록 방지, 삭제 시 원본·청크·벡터 제거, 잘못된 출처·허위 인용 거부, 공개 평가문 검색 누출 방지, 잘못된 입력 처리, PDF 텍스트 추출·페이지 렌더링, 테스트 임베딩을 사용한 FAISS 검색.

**아직 검증하지 않은 항목:** Streamlit의 업로드·검색·매칭 전체 사용자 흐름, 이 저장소에서의 HF 다운로드 재현, Ollama 모델을 사용한 추론·임베딩, VLM 응답, Docker 배포. 모델 실행 결과나 성능 수치는 아직 없습니다.

직접 평가할 때는 JD·개인 문서 5~10쌍에 사람이 요구사항과 근거를 표시하고, 검색 성공·인용 정확성·근거 없는 주장을 기록하세요. 동일 공고·지원서가 학습과 평가 양쪽에 겹치지 않도록 문서 단위로 분리합니다.

필수 근거 커버리지는 직접 근거 1, 관련 경험 0.5, 근거 없음 0의 평균입니다. 검색 전용 판정 대기에는 계산하지 않습니다. 합격 가능성이나 기업의 채용 점수가 아닙니다.

## 참고자료

- [Resume Matching Dataset v2](https://huggingface.co/datasets/jminc/resume-matching-dataset-v2)
- [Ollama Chat API](https://docs.ollama.com/api/chat)
- [Ollama Embed API](https://docs.ollama.com/api/embed)
- [EmbeddingGemma](https://ollama.com/library/embeddinggemma)
- [Qwen2.5-VL 3B](https://ollama.com/library/qwen2.5vl:3b)
- [Streamlit 배포 안내](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app)
