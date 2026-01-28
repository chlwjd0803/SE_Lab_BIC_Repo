import subprocess

def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout

current_hash = run_command("git rev-parse HEAD").strip() # 혹은 현재 실패한 부모 해시 입력

while True:
    print(f"🔍 현재 검증 중인 커밋: {current_hash}")
    
    # 1. 부모 커밋 찾기
    parent_hash = run_command(f"git log -1 --pretty=format:%P {current_hash}").strip()
    if not parent_hash:
        print("❌ 더 이상 거슬러 올라갈 부모 커밋이 없습니다.")
        break
        
    # 2. 소스 코드 교체 (Partial Restore)
    run_command("git restore src/")
    run_command(f"git restore --source={parent_hash} src/")
    run_command("git restore src/test/java/org/apache/commons/lang3/reflect/TypeUtilsTest.java")
    
    # 3. 테스트 실행
    run_command("defects4j compile")
    test_output = run_command("defects4j test -t org.apache.commons.lang3.math.NumberUtilsTest::TestLang747")
    
    if "Failing tests: 0" in test_output:
        print(f"🎊 BIC 발견! 범인은 [{current_hash}] 입니다!")
        print(f"이전 커밋 [{parent_hash}] 에서는 정상 작동(PASS)함을 확인했습니다.")
        break
    else:
        print("... 여전히 FAIL. 더 과거로 이동합니다.")
        current_hash = parent_hash