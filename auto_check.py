import subprocess
import ollama

# 1. 설정
cwd_path = "/workspace/SE_Lab_BIC_Repo/lang_1_buggy"
blame_cmd = "git blame -L 464,475 src/main/java/org/apache/commons/lang3/math/NumberUtils.java"

print("1. [사용자 정의 규칙] 기반 정밀 분석을 시작합니다 (대화 기록 완전 초기화)...")

# 후보 추출
result = subprocess.check_output(blame_cmd, shell=True, text=True, cwd=cwd_path)
unique_hashes = list({line.split()[0] for line in result.strip().split('\n')})

final_candidates = []

# 2. 분석 루프
for h in unique_hashes:
    print(f"--- 분석 중: [{h}] ---")
    
    # 실제 코드 변경점(diff) 추출
    show_cmd = f"git show -p {h} -- src/main/java/org/apache/commons/lang3/math/NumberUtils.java"
    diff_content = subprocess.check_output(show_cmd, shell=True, text=True, cwd=cwd_path)
    
    # [사용자님의 3대 규칙 + Few-shot 프롬프트]
    # 모델에게 정답 예시를 보여줘서 입을 막습니다.
    prompt = f"""
    [SYSTEM]
    You are a strict code analysis machine. 
    Rule 1: NO explanations. Answer ONLY with the tag.
    Rule 2 (For REFACTORING): NEVER use the word "functional" or "function". Tag: [RESULT: REFACTORING]
    Rule 3 (For FUNCTIONAL): MUST use "functional". NEVER use "refactoring". Tag: [RESULT: FUNCTIONAL]

    [EXAMPLES]
    Input: Diff showing only 'final' added to a variable.
    Output: [RESULT: REFACTORING]

    Input: Diff showing a change in an 'if' condition or a new calculation.
    Output: [RESULT: FUNCTIONAL]

    [ACTUAL DATA TO ANALYZE]
    {diff_content}

    [FINAL ANSWER]
    """
    
    # ollama.generate를 사용하여 대화 맥락이 섞이는 것을 원천 차단합니다.
    response = ollama.generate(model='llama3:8b', prompt=prompt)
    res_text = response['response'].strip().upper()
    
    print(f"LLM 판결: {res_text}")

    # [사용자님의 필터링 로직 반영]
    # 리팩토링일 때 'functional'을 절대 안 쓰기로 했으므로, 
    # '[RESULT: FUNCTIONAL]'이라는 정확한 태그가 있을 때만 바구니에 담습니다.
    if '[RESULT: FUNCTIONAL]' in res_text:
        final_candidates.append(h)
        print(">> 상태: BIC 후보 추가")
    else:
        print(">> 상태: 제외됨 (리팩토링)")

print("\n" + "="*50)
print(f"--- [최종 필터링 완료]: {final_candidates}")
print("="*50)

# 결과 저장
with open("bic_candidates.txt", "w") as f:
    for c in final_candidates:
        f.write(c + "\n")