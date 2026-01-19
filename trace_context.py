import javalang
import os

# 1. 설정
PROJECT_ROOT = "/workspace/SE_Lab_BIC_Repo/lang_1_buggy"
# 제외할 메서드/클래스 키워드 (토큰 절약용)
BLACKLIST = ['valueOf', 'toString', 'hashCode', 'equals', 'doubleValue', 'longValue', 'abs', 'min', 'max']

def is_blacklisted(method_name):
    return any(name == method_name for name in BLACKLIST)

def get_refined_context(project_root, target_file, target_line):
    full_path = os.path.join(project_root, target_file)
    with open(full_path, 'r', encoding='utf-8') as f:
        code = f.read()

    tree = javalang.parse.parse(code)
    
    # 분석 대상 라인의 메서드 노드 찾기
    target_method = None
    for path, node in tree.filter(javalang.tree.MethodDeclaration):
        if node.position and node.position.line <= target_line:
            target_method = node

    if not target_method:
        return "Target method not found."

    # 호출된 메서드 중 블랙리스트가 아닌 것만 추출
    calls = set()
    for path, node in target_method.filter(javalang.tree.MethodInvocation):
        if not is_blacklisted(node.member):
            calls.add(node.member)

    context_snippets = []
    for m_name in calls:
        # 프로젝트 내에서 해당 메서드의 '핵심 정의'만 탐색
        for root, dirs, files in os.walk(project_root):
            for file in files:
                # 같은 패키지나 math 관련 패키지에 집중 (필터링 조건 강화)
                if file.endswith(".java") and ("math" in root or "mutable" in root):
                    path = os.path.join(root, file)
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            # public/static 메서드 정의부만 타겟팅 (단순 호출부 제외)
                            if f" {m_name}(" in line and ("public" in line or "static" in line):
                                # 위아래 10라인씩만 제한적으로 추출
                                snippet = "".join(lines[max(0, i-2):min(len(lines), i+12)])
                                context_snippets.append({
                                    "file": file,
                                    "method": m_name,
                                    "snippet": snippet
                                })
                                break # 한 파일에서 하나 찾으면 중단
    return context_snippets

# 실행 예시
results = get_refined_context(PROJECT_ROOT, "src/main/java/org/apache/commons/lang3/math/NumberUtils.java", 464)

for res in results:
    print(f"📍 [Filtered Context] {res['file']} -> {res['method']}")
    # print(res['snippet']) # 여기서 필요한 것만 선택적으로 출력