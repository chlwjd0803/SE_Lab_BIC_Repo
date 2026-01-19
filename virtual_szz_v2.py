import subprocess
import os
import javalang
import ollama

# --- 1. 연구 환경 설정 ---
PROJECT_ROOT = "/workspace/SE_Lab_BIC_Repo/lang_1_buggy"
# Git이 인식하는 실제 경로 (git ls-files 결과 반영)
GIT_TARGET_PATH = "src/main/java/org/apache/commons/lang3/math/NumberUtils.java"
TARGET_FILES_FOR_CONTEXT = ["NumberUtils.java", "Fraction.java"]
BLAME_RANGE = "464,475"
BUG_SYMPTOM = "createNumber('0.E1') 입력 시 NumberFormatException이 발생하지 않거나 타입이 잘못 변환됨."

# --- 2. 유틸리티 및 데이터 추출 ---

def run_cmd(cmd, cwd=PROJECT_ROOT):
    return subprocess.check_output(cmd, shell=True, text=True, cwd=cwd)

def get_parent_hash(commit_hash):
    """해당 커밋의 부모 해시를 가져옴"""
    return run_cmd(f"git rev-parse {commit_hash}^").strip()

def extract_context(commit_hash):
    """특정 시점의 코드 문맥 추출"""
    run_cmd(f"git restore --source={commit_hash} src/")
    # 실제 디스크에 파일이 어디 있는지 찾아서 읽음 (D4J 버전 차이 대응)
    actual_path = None
    for root, _, files in os.walk(PROJECT_ROOT):
        if "NumberUtils.java" in files:
            actual_path = os.path.join(root, "NumberUtils.java")
            break
            
    if not actual_path: return "Context missing"
    
    with open(actual_path, 'r', encoding='utf-8') as f:
        content = f.read()
    run_cmd("git restore src/")
    return content

# --- 3. 비교 분석형 LLM 요청 ---

def compare_analyze_llm(h, p_h, h_context, p_context, diff):
    prompt = f"""
    [ROLE] 소프트웨어 공학 BIC 식별 전문가
    [TASK] 후보 커밋({h})과 부모 커밋({p_h})을 비교하여, 이 지점에서 버그가 유발되었는지 판정하라.

    [버그 증상] {BUG_SYMPTOM}

    [1. 부모 커밋 상태 (Parent: {p_h})]
    {p_context[:2000]}... (생략됨)

    [2. 후보 커밋 변경 사항 (Diff)]
    {diff}

    [3. 후보 커밋 최종 코드 (Candidate: {h})]
    {h_context[:2000]}... (생략됨)

    [분석 가이드라인]
    - 부모 커밋에서는 '0.E1' 처리가 어떻게 이루어지는가?
    - 후보 커밋에서 추가/수정된 로직이 '0.E1'을 잘못된 경로로 유도하는가?
    - 단순 리팩토링(주석, final 등)이라면 무조건 NOT_BIC이다.
    - PASS(부모) -> FAIL(후보)로 변하는 '의미론적 변화'를 포착하라.

    [결과 형식]
    RESULT: [BIC / NOT_BIC]
    REASON: (구체적인 가상 실행 비교 결과)
    """
    response = ollama.generate(model='llama3:8b', prompt=prompt)
    return response['response']

# --- 4. 메인 실행 루프 ---

def main():
    print(f"🚀 [SZZ 기반 비교 분석] 가상 실행 파이프라인 가동")
    try:
        # 1. 후보군 추출
        output = run_cmd(f"git blame -L {BLAME_RANGE} {GIT_TARGET_PATH}")
        candidates = list({line.split()[0] for line in output.strip().split('\n')})
        print(f"발견된 후보군: {candidates}")

        for h in candidates:
            print(f"\n" + "="*60 + f"\n🔍 후보 분석: {h}")
            try:
                p_h = get_parent_hash(h)
                diff = run_cmd(f"git show {h} -- {GIT_TARGET_PATH}")
                
                # 부모와 자식의 문맥을 각각 추출
                h_context = extract_context(h)
                p_context = extract_context(p_h)
                
                print(f"🤖 부모({p_h}) vs 후보({h}) 비교 추론 중...")
                result = compare_analyze_llm(h, p_h, h_context, p_context, diff)
                print(f"\n[분석 결과]\n{result}")
                
            except Exception as e:
                print(f"❌ {h} 분석 오류: {e}")
                
    except Exception as e:
        print(f"❌ 초기화 에러: {e}")

if __name__ == "__main__":
    main()