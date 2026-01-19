import subprocess
import os
import ollama

# --- 1. 연구 환경 및 설정 ---
PROJECT_ROOT = "/workspace/SE_Lab_BIC_Repo/lang_1_buggy"
BUG_SYMPTOM = "createNumber('0.E1') 입력 시 NumberFormatException이 발생하지 않거나 타입 변환 오류 발생"
BLAME_RANGE = "464,475"

# --- 2. 유틸리티 함수 (Git & 경로 관리) ---

def run_cmd(cmd, cwd=PROJECT_ROOT):
    return subprocess.check_output(cmd, shell=True, text=True, cwd=cwd)

def get_target_path():
    """Git 인덱스에서 실제 NumberUtils.java 경로 탐색"""
    try:
        paths = run_cmd("git ls-files | grep NumberUtils.java").splitlines()
        for p in paths:
            if "math" in p: return p
        return paths[0]
    except:
        return None

GIT_PATH = get_target_path()

# --- 3. [Stage 1] 정적 리팩토링 필터 (Static Filter) ---

def static_filter_step(commit_hash):
    """커밋의 성격(Refactoring vs Functional) 판별"""
    try:
        diff = run_cmd(f"git show -p {commit_hash} -- {GIT_PATH}")
    except:
        return "ERROR"

    prompt = f"""
    [SYSTEM] You are a strict code analysis machine.
    Rule 1: Answer ONLY with the tag.
    Rule 2 (REFACTORING): Only 'final', comments, variable rename, or formatting changes. Tag: [REFACTORING]
    Rule 3 (FUNCTIONAL): Any change in 'if' conditions, calculations, or logic flow. Tag: [FUNCTIONAL]

    [DATA]
    {diff}

    [RESULT]
    """
    response = ollama.generate(model='llama3:8b', prompt=prompt)
    res = response['response'].strip().upper()
    return "FUNCTIONAL" if "[FUNCTIONAL]" in res else "REFACTORING"

# --- 4. [Stage 2] 가상 실행 토너먼트 (Virtual Execution) ---

def virtual_trace_step(commit_hash, round_num):
    """부모 커밋과 대조하여 실제 버그 유발 여부 정밀 분석"""
    try:
        p_hash = run_cmd(f"git rev-parse {commit_hash}^").strip()
        diff = run_cmd(f"git show {commit_hash} -- {GIT_PATH}")
        # 해당 시점의 코드 조각 추출 (지역성 20줄)
        context = run_cmd(f"git show {commit_hash}:{GIT_PATH}")
    except:
        return "ERROR"

    prompt = f"""
    [ROLE] SW 정적 분석 전문가 (Round {round_num})
    [TASK] '0.E1' 입력 시 데이터 흐름을 추론하여 BIC 여부를 확정하라.
    
    [버그 증상] {BUG_SYMPTOM}
    [변경 사항(Diff)] {diff}
    
    [가이드라인]
    1. '0.E1'이 이 코드의 조건문 분기를 탈 때, 부모 커밋과 다른 결과가 나오는지 확인하라.
    2. 가상 실행 테이블(Line | Logic | Result)을 반드시 작성하라.
    3. 최종 결과는 'RESULT: [BIC / NOT_BIC]' 형식으로 제출하라.

    [판정]
    """
    response = ollama.generate(model='llama3:8b', prompt=prompt)
    return response['response']

# --- 5. 메인 파이프라인 엔진 ---

def main():
    if not GIT_PATH:
        print("❌ 경로를 찾을 수 없습니다."); return

    print(f"📡 [1단계] 후보군 추출 및 리팩토링 필터링 시작...")
    blame_out = run_cmd(f"git blame -L {BLAME_RANGE} --porcelain {GIT_PATH}")
    initial_hashes = list({line.split()[0][:10] for line in blame_out.strip().split('\n') if len(line.split()[0]) == 40})
    
    functional_candidates = []
    for h in initial_hashes:
        status = static_filter_step(h)
        print(f"   - {h}: {status}")
        if status == "FUNCTIONAL":
            functional_candidates.append(h)

    print(f"\n✅ 필터링 완료: {len(functional_candidates)}개의 로직 변경 커밋 발견")
    
    candidates = functional_candidates
    round_num = 1
    
    while len(candidates) > 1:
        print(f"\n🏆 [2단계] 가상 실행 토너먼트 라운드 {round_num}")
        bic_winners = []

        for h in candidates:
            print(f"   - {h} 심층 분석 중...", end="", flush=True)
            res = virtual_trace_step(h, round_num)
            
            if "RESULT: BIC" in res:
                bic_winners.append(h)
                print(" 🎯 BIC 판정")
            else:
                print(" ❌ 탈락")

        if not bic_winners:
            print("   ⚠️ 모든 후보가 탈락하여 현재 후보군을 재검토합니다.")
            round_num += 1; continue
        
        candidates = bic_winners
        if len(candidates) == 1: break
        round_num += 1
        if round_num > 4: break

    print(f"\n" + "="*50)
    print(f"🎊 최종 확정된 BIC: {candidates}")
    print("="*50)

if __name__ == "__main__":
    main()