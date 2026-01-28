# 🚀 LLM 기반 BIC(버그 유발 커밋) 식별 연구 가이드 (v1.3)

이 가이드는 **영남대학교 SE Lab**에서 **Defects4J** 데이터셋과 **LLM(Ollama)**을 활용하여 버그의 원인이 된 과거 커밋(BIC)을 정교하게 식별하는 연구 환경 구축 및 분석 워크플로우를 다룹니다.

---

## 1. 시스템 필수 패키지 설치 (Root 권한 필요)
빈 서버(Ubuntu 기준)에서 가장 먼저 실행해야 하는 환경 설정입니다. Defects4J 운영에 필요한 Perl 및 Java 8, 기타 빌드 도구를 포함합니다.

```bash
# 1. 패키지 목록 업데이트 및 필수 빌드 도구 설치
sudo apt update
sudo apt install -y build-essential git curl wget unzip zip perl \
               libdbi-perl libdbd-csv-perl \
               python3 python3-pip cpanminus tree

# 가상환경일 때 다음 명령어를 통해 안전한 경로임을 명시
git config --global --add safe.directory /workspace/SE_Lab_BIC_Repo

# 2. SDKMAN 설치 및 Java 설정
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"

# Java 11 (Temurin) 설치 (D4J v3 실행용)
sdk install java 11.0.22-tem

# Java 8 사용 설정 변경
sdk use java 11.0.22-tem

# Java 8 설치 (과거 프로젝트 호환성 대비)
sdk install java 8.0.402-tem

# Java 8 사용 설정 변경
sdk use java 8.0.402-tem

# 시스템 기본값으로 고정 (터미널 다시 켜도 유지됨)
sdk default java 11.0.22-tem
sdk default java 8.0.402-tem
```

---

## 2. Defects4J & Ollama 환경 구축
```bash
# 1. 연구용 메인 디렉토리 생성 및 이동
mkdir -p ~/llmszz_v1
cd ~/llmszz_v1

# 2. Defects4J 저장소 클론 및 설치
git clone https://github.com/rjust/defects4j.git
git clone https://github.com/rjust/defects4j.git -b v2.0.0
cd defects4j
sudo cpanm --installdeps .
./init.sh

# 3. 환경 변수 등록 (~/.bashrc)
echo "export PATH=\$PATH:$(pwd)/framework/bin" >> ~/.bashrc
source ~/.bashrc

# 4. Ollama(LLM) 설치 및 모델 다운로드
# 아래 명령어로 GPU와 연결됨을 반드시 확인하기
nvidia-smi

# 하드웨어 연결용
sudo apt update && sudo apt install -y pciutils lshw

curl -fsSL https://ollama.com/install.sh | sh
ollama serve > /dev/null 2>&1 & # 로그 리다이렉션으로 터미널 보호
ollama pull llama3:8b
pip3 install ollama
```

---

## 3. 프로젝트 버전 관리 (Buggy vs Fixed)

BIC 탐지를 위해 버그가 있는 상태(`b`)와 고쳐진 상태(`f`)를 각각 체크아웃하여 비교하는 과정이 필수적입니다.
아래 명령어는 1 버전의 체크아웃 예시이며 실제로 다른 넘버링이나 lang말고 다른 버전도 존재합니다.

### 3.1 버전별 체크아웃 방법
```bash
cd ~/llmszz_v1
mkdir -p analysis/lang_1 && cd analysis/lang_1

# Lang 1번 버그의 Buggy 버전(1b) 가져오기: 버그 재현용
defects4j checkout -p Lang -v 1b -w ./lang_1_buggy

# Lang 1번 버그의 Fixed 버전(1f) 가져오기: 정답 비교용
defects4j checkout -p Lang -v 1f -w ./lang_1_fixed

```

### 3.2 버전 비교 요약
| 구분 | Buggy 버전 (`1b`) | Fixed 버전 (`1f`) |
| :--- | :--- | :--- |
| **상태** | 버그 포함 (테스트 실패) | 버그 수정됨 (테스트 통과) |
| **주요 용도** | `git blame` 실행 및 BIC 추적 | 수정 패치(정답) 확인 및 LLM 컨텍스트 |
---

### 3.3 기본 명령어

```bash
defects4j compile
defects4j test
defects4j coverage
```


---

## 4. 버그 분석 및 비교 방법 (추적의 핵심) - 임시 폐기

### 방법 1: `diff`를 이용한 코드 차이점 분석
```bash
# 두 폴더 사이의 소스 코드 변경 사항 직접 비교 (루트 디렉토리에서 실행)
diff -ur ./lang_1_buggy/src/main/java ./lang_1_fixed/src/main/java
```

### 방법 2: Defects4J 제공 패치(Patch) 파일 확인 (권장)
```bash
# Lang 1번 버그의 공식 수정 패치 열람
cat ~/llmszz_v1/defects4j/framework/projects/Lang/patches/1.src.patch
```

---

## 5. BIC 추적 실습 (SZZ + LLM)

### 5.1 Git Blame으로 후보군 추출
```bash
# 예: NumberUtils.java의 464~485 라인을 수정한 과거 이력 확인
git blame -L 464,485 src/main/java/org/apache/commons/lang3/math/NumberUtils.java
```

### 5.2 [중요] 동적 검증 전략: `git restore` 활용
`git checkout`은 D4J의 빌드 환경 설정을 파괴하므로, 환경은 고정하고 소스 코드만 교체하는 방식을 사용합니다.

```bash
# 1. 다시 깨끗하게 초기화
git restore src/

# 2. 메인과 테스트를 모두 '동일한' 과거 시점으로 복구
git restore --source={COMMIT_HASH} src/main/
git restore --source={COMMIT_HASH} src/test/

# 3. 컴파일 노이즈 제거 (Java 11 호환성 에러 파일만 현재 버전으로 복구)
git restore src/test/java/org/apache/commons/lang3/reflect/TypeUtilsTest.java

# 4. 빌드 및 특정 버그 재현 테스트 실행
defects4j compile
defects4j test -t org.apache.commons.lang3.math.NumberUtilsTest::TestLang747
```

---

## 6. 영남대 SE Lab BIC 연구용 도커 관리 치트시트

### 6.1 컨테이너 관리
```bash
# 현재 상태 세이브 (Snapshot)
docker commit [CONTAINER_ID] my_research_env:backup_v1

# 저장된 이미지로 새 컨테이너 생성 (GPU 가속 포함)
docker run -it --name research_java8_test \
  --gpus all \
  -v /data/cj/SE_Lab_BIC_Repo:/workspace/SE_Lab_BIC_Repo \
  my_research_env:working_backup /bin/bash

# 컨테이너 일상 관리
docker start research_java8_test
docker exec -it research_java8_test /bin/bash
docker stop research_java8_test
```

### 6.2 팁
* **컨테이너 진출**: `Ctrl + P` -> `Ctrl + Q` (끄지 않고 연결만 끊기)
* **환경 변수**: 버전 충돌 시 `sudo update-alternatives --config java` 활용.

---

## SE Lab 연구 일지 (2026-01-28)




## 📝 SE Lab 연구 일지 (2026-01-19)

### 📂 주요 성과 및 병목 지점 분석
* **환경 유실(Environment Decay) 문제 직면**: Defects4J v3.0 기반 과거 커밋(2013년 등) 복구 시 Java 버전 및 의존성 불일치로 빌드 성공률 급격히 저하(30~50% 미만). 동적 검증의 물리적 한계 확인.
* **가상 실행(Virtual Execution) 도입**: 물리적 빌드 없이 LLM의 추론력을 이용해 코드를 분석하는 '의존성 기반 문맥 확장' 및 '지역성 기반 분석' 시도.
* **LLM 환각(Hallucination) 실증**: 패키지 경로 변경으로 인해 빈 문맥(Empty Context)이 전달되었음에도 LLM이 BIC라고 확신하며 허구의 논리를 생성하는 현상 포착.
* **통합 파이프라인 구축**: 리팩토링 커밋을 걸러내는 **[정적 필터]**와 결과가 나올 때까지 반복하는 **[토너먼트 검증]**을 결합한 통합 엔진 설계.

### 🧠 핵심 인사이트
1. **가상 실행 기반 BIC 판정의 정의**:
   $$BIC = \{C_i \mid \text{VirtualTest}(C_i, \text{Path}_{dep}) = \text{FAIL} \land \text{VirtualTest}(C_{i-1}, \text{Path}_{dep}) = \text{PASS}\}$$
   (단, $\text{VirtualTest}$는 LLM의 가상 실행 추론 결과, $\text{Path}_{dep}$는 추출된 문맥을 의미함)
2. **반복 검증을 통한 수렴**: 소형 모델(Llama 3 8B)의 확률적 추론에 의한 번복 현상을 극복하기 위해 다회차 라운드(최대 6회)를 수행, 결과가 하나로 수렴되는 과정을 확인.



### 🔍 실험 결과 및 분석 (Target: Lang_1)
* **최종 수렴 후보**: `d844d1eb5e` (6라운드 토너먼트 끝에 단일 후보로 압축됨).
* **결과 분석**: 
    * 해당 커밋은 16진수 접두사(`#`, `0X` 등) 처리 로직을 강화함. 
    * LLM은 이 로직의 추가가 `"0.E1"` 파싱 경로에 간섭했다고 판단함.
    * 다만, 이것이 실제 정답(Ground Truth)인지 혹은 단순한 패턴 매칭에 의한 수렴인지는 추가적인 정밀 검증이 필요함 (모델의 판단을 100% 신뢰하기엔 환각 위험이 상존함).



### 🚩 향후 과제
- [ ] **컨텍스트 최적화(Context Diet)**: LLM의 정보 과부하를 막기 위해 불필요한 노이즈를 제거하는 전처리 알고리즘 고도화.
- [ ] **프롬프트 엔지니어링 정밀화**: 라마 모델의 논리력 보완을 위해 변수 상태 변화를 **표(Table) 형식**으로 강제하는 가이드라인 적용.
- [ ] **대형 모델 대조군 실험**: 70B 이상급 모델과의 성능 비교를 통해 현재 도출된 수렴 결과의 타당성 검토.


## 📝 SE Lab 연구 일지 (2026-01-16)

### 📂 주요 성과
* **D4J 환경 무결성 이슈 해결**: `git checkout`이 빌드 환경을 파괴함을 확인하고 `git restore --source` 전략으로 선회하여 빌드 성공률 100% 확보.
* **Java 11 컴파일 에러 대응**: 과거 제네릭 추론 에러를 유발하는 `TypeUtilsTest`를 부분 복구하여 전체 빌드 성공.
* **LLM 후보 필터링**: Llama3:8b 모델을 통해 SZZ 후보 중 리팩토링 커밋 제외 및 로직 변경 후보(`b3db6ed9ef`, `e2ba8bc288`) 선별.
* **BIC 경계선 탐색**: `b3db6ed9ef`와 부모 커밋 `5df8f55e` 대조 테스트 결과, 두 지점 모두 FAIL임을 확인 -> 범인은 더 과거에 있음을 증명.

### 🧠 핵심 인사이트
1. **BIC 판정의 수학적 정의**:
   $$BIC = \{C_i \mid \text{test}(C_i) = \text{FAIL} \land \text{test}(\text{parent}(C_i)) = \text{PASS}\}$$
2. **동적 검증의 필연성**: 정적 분석만으로는 가짜 범인(False Positive)을 걸러낼 수 없으며, 반드시 상태 변화(PASS $\to$ FAIL)를 증명하는 테스트가 수반되어야 함.

### 🚩 향후 과제
- [ ] `5df8f55e` 이전 히스토리 전수 조사하여 최초의 `PASS` 지점 도출.
- [ ] `git restore` -> `compile` -> `test` 자동화 루프 스크립트 고도화.


