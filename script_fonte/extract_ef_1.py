import xml.etree.ElementTree as ET

def extract_failure_coverage(xml_path):
    """
    coverage.xml 파일에서 hits > 0 인 라인(Ef)을 추출합니다.
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ef_set = set() # 중복 방지를 위해 set 사용

        # 모든 class 태그를 찾습니다.
        for cls in root.findall(".//class"):
            class_name = cls.get('name')
            
            # 해당 클래스 내의 모든 line 태그를 확인합니다.
            for line in cls.findall(".//line"):
                hits = int(line.get('hits'))
                
                # 실행 횟수(hits)가 0보다 큰 경우만 Ef에 추가합니다.
                if hits > 0:
                    line_number = line.get('number')
                    ef_set.add((class_name, line_number))
        
        return sorted(list(ef_set)) # 보기 좋게 정렬하여 반환

    except Exception as e:
        print(f"파일을 읽는 중 오류 발생: {e}")
        return []

# 실행 예시
if __name__ == "__main__":
    ef_data = extract_failure_coverage('../lang_13_buggy/coverage.xml')
    
    print(f"추출된 실패 관련 코드 라인 수: {len(ef_data)}개")
    print("--- 추출 결과 (일부) ---")
    for class_name, line_num in ef_data[:10]:
        print(f"클래스: {class_name}, 라인: {line_num}")