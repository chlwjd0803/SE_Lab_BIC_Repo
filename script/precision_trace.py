import javalang
import os

# 1. 연구 환경 설정
PROJECT_ROOT = "/workspace/SE_Lab_BIC_Repo/lang_1_buggy"
# 우리가 '범인' 후보로 의심하며 코드를 들여다볼 핵심 파일 리스트
TARGET_FILES = ["NumberUtils.java", "Fraction.java"] 
START_FILE = "src/main/java/org/apache/commons/lang3/math/NumberUtils.java"
START_LINE = 464 # 분석 시작점

def get_method_at_line(tree, line):
    """지정된 라인이 속한 메서드 노드 추출"""
    target_node = None
    for path, node in tree.filter(javalang.tree.MethodDeclaration):
        if node.position and node.position.line <= line:
            target_node = node
    return target_node

def find_definition_in_targets(method_name, project_root, target_files):
    """지정된 TARGET_FILES 내에서만 메서드 정의를 찾음 (신뢰 경계 설정)"""
    matches = []
    for root, dirs, files in os.walk(project_root):
        for file in files:
            if file in target_files: # 오직 우리가 지정한 파일들만 검사
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        # 메서드 정의부 패턴 매칭 (추상 메서드 제외)
                        if f" {method_name}(" in line and ("public" in line or "static" in line or "private" in line) and "{" in line:
                            # 가상 실행에 필요한 전후 맥락 15라인 추출
                            snippet = "".join(lines[max(0, i-2):min(len(lines), i+13)])
                            matches.append({
                                "file": file,
                                "line": i + 1,
                                "snippet": snippet
                            })
                            break
    return matches

# --- 실행 로직 ---

print(f"🎯 [집중 분석 시작]: {START_FILE} (L{START_LINE})")
print(f"🔍 [검사 범위]: {TARGET_FILES} 내의 상호 호출\n")

full_path = os.path.join(PROJECT_ROOT, START_FILE)
with open(full_path, 'r', encoding='utf-8') as f:
    code = f.read()

tree = javalang.parse.parse(code)
current_method = get_method_at_line(tree, START_LINE)

if current_method:
    print(f"🚀 현재 분석 중인 메서드: '{current_method.name}'")
    
    # 메서드 내부의 호출부 추출
    invocations = set()
    for path, node in current_method.filter(javalang.tree.MethodInvocation):
        invocations.add(node.member)

    for m_name in invocations:
        # 핵심 파일들(NumberUtils, Fraction 등) 내에 정의가 있는지 탐색
        defs = find_definition_in_targets(m_name, PROJECT_ROOT, TARGET_FILES)
        
        for d in defs:
            print(f"\n✅ [발견] {d['file']}에서 '{m_name}' 정의 확인 (Line {d['line']})")
            print("-" * 50)
            print(d['snippet'])
            print("-" * 50)
else:
    print("❌ 해당 라인에서 메서드를 찾을 수 없습니다.")