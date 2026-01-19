import subprocess
import os
import ollama

# --- 1. 연구 환경 및 설정 ---
PROJECT_ROOT = "/workspace/SE_Lab_BIC_Repo/lang_1_buggy"
BUG_SYMPTOM = "createNumber('0.E1') 입력 시 NumberFormatException이 발생해야 함에도 잘못된 로직을 타거나 타입 변환 오류 발생"

# --- 2. 경로 자동 탐지 및 유틸리티 ---

def run_cmd(cmd, cwd=PROJECT_ROOT):
    return subprocess.check_output(cmd, shell=True, text=True, cwd=cwd)

def get_git_target_path():
    """Git이 현재 추적 중인 NumberUtils.java의 경로를 반환"""
    try:
        # Git 인덱스에서 파일 경로를 찾음
        paths = run_cmd("git ls-files | grep NumberUtils.java").splitlines()
        # 'math' 패키지가 포함된 경로를 우선적으로 선택
        for p in paths:
            if "math" in p:
                return p
        return paths[0]
    except:
        return None

# Git이 인식하는 주소 자동 설정
GIT_TARGET_FILE = get_git_target_path()
BLAME_RANGE = "464,475"

def extract_local_context(commit_hash, line_num, window=20):
    """지정된 라인 주변의 문맥만 추출"""
    try:
        # Git 저장소 내의 파일 내용을 가져옴
        content = run_cmd(f"git show {commit_hash}:{GIT_TARGET_FILE}")
        lines = content.splitlines()
        
        idx = int(line_num) - 1
        start = max(0, idx - window)
        end = min(len(lines), idx + window + 1)
        
        return "\n".join(lines[start:end])
    except:
        return "Context extraction failed."

# --- 3. 지역성 집중형 LLM 분석 함수 ---

def ask_llm_local_analysis(commit_hash, diff, context, round_num):
    prompt = f"""
    [ROLE] 소프트웨어 정적 분석 전문가 (라운드 {round_num})
    [TASK] 제공된 코드 조각만 분석하여 커밋({commit_hash})이 BIC인지 판정하라.

    [버그 증상] {BUG_SYMPTOM}
    [수정된 코드(Diff)]
    {diff}
    [주변 문맥]
    {context}

    [엄격한 가이드라인]
    1. 외부 메서드(createFloat 등)는 정상이라 가정하고, 현재 코드의 'if/else' 조건문 분기에만 집중하라.
    2. '0.E1'이 입력되었을 때, 이 코드의 몇 번째 라인에서 잘못된 분기로 빠지는지 단계별로 추론하라.
    3. 단순 리팩토링(final 추가, 주석 수정 등)은 절대 BIC가 아니다.
    4. 가상 실행 과정을 표(Line | Logic | Result)로 작성하라.

    [판정 결과]
    RESULT: [BIC / NOT_BIC]
    """
    response = ollama.generate(model='llama3:8b', prompt=prompt)
    return response['response']

# --- 4. 메인 토너먼트 루프 ---

def main():
    if not GIT_TARGET_FILE:
        print("❌ 에러: Git 저장소에서 NumberUtils.java를 찾을 수 없습니다.")
        return

    print(f"🚀 [지역성 토너먼트] 시작 (Target: {GIT_TARGET_FILE})")
    
    # 1. 후보군 추출
    try:
        output = run_cmd(f"git blame -L {BLAME_RANGE} --porcelain {GIT_TARGET_FILE}")
        candidates_info = {}
        for line in output.strip().split('\n'):
            parts = line.split()
            if len(parts) > 1 and len(parts[0]) == 40:
                h = parts[0][:10]
                l = parts[2]
                candidates_info[h] = l
        
        candidates = list(candidates_info.keys())
        print(f"📦 초기 후보군: {candidates}")
    except Exception as e:
        print(f"❌ Blame 에러: {e}")
        return

    round_num = 1
    while len(candidates) > 1:
        print(f"\n🏆 라운드 {round_num} (남은 후보: {len(candidates)}개)")
        bic_found = []

        for h in candidates:
            print(f"🔍 {h} 분석 중...", end="", flush=True)
            try:
                diff = run_cmd(f"git show {h} -- {GIT_TARGET_FILE}")
                context = extract_local_context(h, candidates_info[h])
                
                res = ask_llm_local_analysis(h, diff, context, round_num)
                
                if "RESULT: BIC" in res:
                    bic_found.append(h)
                    print(" ✅ BIC")
                else:
                    print(" ❌ NOT")
            except:
                print(" ⚠️ 에러")

        if not bic_found:
            print("\n모두 탈락했습니다. 현재 후보군으로 재검증합니다.")
            round_num += 1
        elif len(bic_found) == 1:
            candidates = bic_found
            print(f"\n🎯 최종 BIC 확정: {candidates[0]}")
            break
        else:
            candidates = bic_found
            round_num += 1
        
        if round_num > 4: break

    if len(candidates) == 1:
        print(f"\n" + "*"*60 + f"\n🎊 최종 BIC: {candidates[0]}\n" + "*"*60)

if __name__ == "__main__":
    main()