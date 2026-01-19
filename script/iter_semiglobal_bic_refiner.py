import subprocess
import os
import javalang
import ollama

# --- 1. 연구 환경 및 설정 ---
PROJECT_ROOT = "/workspace/SE_Lab_BIC_Repo/lang_1_buggy"
GIT_TARGET_PATH = "src/main/java/org/apache/commons/lang3/math/NumberUtils.java"
BLAME_RANGE = "464,475"
BUG_SYMPTOM = "createNumber('0.E1') 입력 시 NumberFormatException이 발생하지 않거나 타입이 잘못 변환됨."

# --- 2. 유틸리티 함수 ---

def run_cmd(cmd, cwd=PROJECT_ROOT):
    return subprocess.check_output(cmd, shell=True, text=True, cwd=cwd)

def extract_context(commit_hash):
    """특정 시점의 코드 전체 문맥 추출"""
    run_cmd(f"git restore --source={commit_hash} src/")
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

# --- 3. 엄격한 규칙이 적용된 LLM 분석 함수 ---

def ask_llm_strict_analysis(commit_hash, parent_hash, diff, context, round_num):
    prompt = f"""
    [ROLE] 소프트웨어 공학 BIC 판정 전문가 (Round {round_num})
    [STRICT RULES]
    1. 리팩토링 규칙: 변수명 변경, final 키워드 추가, 주석 수정, 단순 코드 이동(Logic 변화 없음)은 무조건 'NOT_BIC'로 판정한다.
    2. 가상 실행 테이블: '0.E1' 입력 시 데이터 흐름을 아래 형식으로 반드시 포함하라.
       | Line | Variable | Value | Change Description |
    3. BIC 판정 기준: 부모 커밋에서는 PASS였으나, 해당 커밋의 변경으로 인해 FAIL이 발생하는 '최초의 지점'인가?

    [버그 증상] {BUG_SYMPTOM}
    [후보 커밋] {commit_hash} (Parent: {parent_hash})

    [코드 변경 사항 (Diff)]
    {diff}

    [전체 코드 문맥]
    {context[:2500]}... (생략됨)

    [요구사항]
    위 규칙에 따라 가상 실행 테이블을 작성하고, 최종 결과를 'RESULT: [BIC / NOT_BIC]' 형식으로 제출하라.
    """
    response = ollama.generate(model='llama3:8b', prompt=prompt)
    return response['response']

# --- 4. 반복 검증 메인 루프 (The Tournament) ---

def main():
    print(f"🚀 [BIC 토너먼트] 반복 검증 파이프라인 시작")
    
    # 1. 초기 후보군 추출
    output = run_cmd(f"git blame -L {BLAME_RANGE} {GIT_TARGET_PATH}")
    candidates = list({line.split()[0] for line in output.strip().split('\n')})
    print(f"📦 초기 후보군 ({len(candidates)}개): {candidates}")

    round_num = 1
    while len(candidates) > 1:
        print(f"\n" + "=".center(60, "="))
        print(f"🏆 검증 라운드 {round_num} 시작 (남은 후보: {len(candidates)}개)")
        print("=".center(60, "="))
        
        bic_found_this_round = []

        for h in candidates:
            print(f"\n🔍 분석 중: {h}...", end="", flush=True)
            try:
                p_h = run_cmd(f"git rev-parse {h}^").strip()
                diff = run_cmd(f"git show {h} -- {GIT_TARGET_PATH}")
                context = extract_context(h)
                
                result_text = ask_llm_strict_analysis(h, p_h, diff, context, round_num)
                
                if "RESULT: BIC" in result_text or "RESULT: [BIC]" in result_text:
                    bic_found_this_round.append(h)
                    print(" ✅ BIC 판정")
                else:
                    print(" ❌ NOT_BIC 판정")
            except Exception as e:
                print(f" ⚠️ 에러 발생: {e}")

        # 라운드 결과 정산
        if len(bic_found_this_round) == 0:
            print(f"\n⚠️ 경고: 모든 후보가 NOT_BIC로 판정되었습니다. 후보군을 유지하며 프롬프트를 강화하여 재시도합니다.")
            round_num += 1
            if round_num > 3: break # 무한 루프 방지
        elif len(bic_found_this_round) == 1:
            candidates = bic_found_this_round
            print(f"\n🎯 최종 BIC 발견: {candidates[0]}")
            break
        else:
            print(f"\n♻️ {len(bic_found_this_round)}개의 BIC 중복 발생. 다음 라운드에서 재검증합니다.")
            candidates = bic_found_this_round
            round_num += 1

    if len(candidates) == 1:
        print(f"\n" + "*"*60)
        print(f"🎊 최종 확정된 BIC: {candidates[0]}")
        print("*"*60)
    else:
        print(f"\n결과를 하나로 좁히지 못했습니다. 남은 후보: {candidates}")

if __name__ == "__main__":
    main()