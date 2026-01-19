import subprocess
import os
import javalang
import ollama

# --- 1. 연구 환경 설정 ---
# Git 저장소의 실제 루트 (git rev-parse 결과 반영)
PROJECT_ROOT = "/workspace/SE_Lab_BIC_Repo/lang_1_buggy"

# Git이 인식하는 경로 (git ls-files 결과 반영)
GIT_TARGET_PATH = "src/main/java/org/apache/commons/lang3/math/NumberUtils.java"

# 분석에 참고할 파일 이름들
TARGET_FILES_FOR_CONTEXT = ["NumberUtils.java", "Fraction.java"]
BLAME_RANGE = "464,475"
BUG_SYMPTOM = "createNumber('0.E1') 입력 시 로직 오류로 인해 NumberFormatException이 발생하지 않거나 잘못된 타입으로 변환됨."

# --- 2. 유틸리티 함수 ---

def run_cmd(cmd, cwd=PROJECT_ROOT):
    """Git 저장소 루트에서 명령어를 실행"""
    return subprocess.check_output(cmd, shell=True, text=True, cwd=cwd)

def find_file_on_disk(filename):
    """디스크를 뒤져서 실제 파일의 상대 경로를 찾아냄 (D4J 버전 차이 대응)"""
    for root, _, files in os.walk(PROJECT_ROOT):
        if filename in files:
            # PROJECT_ROOT를 제외한 상대 경로 반환
            full_path = os.path.join(root, filename)
            return os.path.relpath(full_path, PROJECT_ROOT)
    return None

def get_blame_candidates():
    """Git이 알고 있는 경로를 이용해 blame 후보 추출"""
    print(f"🔍 Git Blame 실행 중: {GIT_TARGET_PATH}")
    output = run_cmd(f"git blame -L {BLAME_RANGE} {GIT_TARGET_PATH}")
    return list({line.split()[0] for line in output.strip().split('\n')})

def extract_context_at_commit(commit_hash):
    """특정 커밋 시점으로 코드를 복구하고 실제 위치를 찾아 문맥 추출"""
    # 과거 시점으로 소스 복구
    run_cmd(f"git restore --source={commit_hash} src/")
    
    # 복구된 시점에서 NumberUtils.java의 실제 위치 확인
    actual_path = find_file_on_disk("NumberUtils.java")
    if not actual_path:
        return f"Warning: NumberUtils.java not found at commit {commit_hash}"

    with open(os.path.join(PROJECT_ROOT, actual_path), 'r', encoding='utf-8') as f:
        tree = javalang.parse.parse(f.read())
        
    target_method = None
    for path, node in tree.filter(javalang.tree.MethodDeclaration):
        if node.name == 'createNumber':
            target_method = node
            break
            
    context_snippets = []
    if target_method:
        invocations = {node.member for path, node in target_method.filter(javalang.tree.MethodInvocation)}
        
        for m_name in invocations:
            # Fraction.java 등도 실제 경로를 찾아서 읽음
            m_file_path = find_file_on_disk("Fraction.java") or find_file_on_disk("NumberUtils.java")
            if m_file_path:
                with open(os.path.join(PROJECT_ROOT, m_file_path), 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        if f" {m_name}(" in line and "{" in line:
                            snippet = "".join(lines[max(0, i-2):min(len(lines), i+13)])
                            context_snippets.append(f"[{os.path.basename(m_file_path)} - {m_name}]\n{snippet}")
                            break
    
    # 원상 복구
    run_cmd("git restore src/")
    return "\n".join(context_snippets)

# --- 3. LLM 가상 실행 요청 ---

def analyze_with_llm(commit_hash, diff, context):
    prompt = f"""
    [ROLE] 소프트웨어 공학 연구용 가상 실행 엔진 (Llama 3 8B)
    [TASK] 제공된 커밋이 버그 유발 커밋(BIC)인지 가상 실행을 통해 판정하라.

    [버그 증상]
    {BUG_SYMPTOM}

    [분석 대상 커밋] {commit_hash}
    
    [코드 변경 사항 (DIFF)]
    {diff}

    [관련 코드 문맥 (CONTEXT)]
    {context}

    [요구 사항]
    1. 입력값 '0.E1'이 로직을 통과할 때의 데이터 흐름을 추론(Virtual Trace)하라.
    2. 부모 커밋과 비교하여, 이 커밋에서 버그가 처음 발생했는지(BIC 여부) 판단하라.
    3. 결과 형식: 'RESULT: [BIC/NOT_BIC]'

    [최종 판결]
    """
    response = ollama.generate(model='llama3:8b', prompt=prompt)
    return response['response']

# --- 4. 메인 실행 ---

def main():
    print(f"🚀 BIC 식별 연구 가상 실행 파이프라인 시작")
    try:
        candidates = get_blame_candidates()
        print(f"Found {len(candidates)} candidates: {candidates}")

        for h in candidates:
            print(f"\n" + "="*60)
            print(f"🔍 분석 중인 커밋: {h}")
            
            try:
                # Git은 GIT_TARGET_PATH(lang3 구조)로 조회
                diff = run_cmd(f"git show {h} -- {GIT_TARGET_PATH}")
                # 실제 파일은 디스크에서 찾아서 분석
                context = extract_context_at_commit(h)
                
                print("🤖 LLM 가상 실행 추론 중...")
                result = analyze_with_llm(h, diff, context)
                print(f"\n[분석 결과]\n{result}")
                
            except Exception as e:
                print(f"❌ 커밋 {h} 분석 실패: {e}")
                
    except Exception as e:
        print(f"❌ 초기화 에러: {e}")

if __name__ == "__main__":
    main()