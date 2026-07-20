# HWPX 이미지 내장 내보내기 패치 명세 및 분석 (HWPX Image Embedding Export Patch)

이 문서는 HWPX 문서 내보내기 시 이미지가 정상적으로 출력되지 않고 빈 점선 프레임(엑박)으로 나타나는 현상을 방지하기 위해 적용된 몽키패치의 분석 및 명세를 다룹니다.

---

## 1. 문제 현상 (Symptom)
* HWPX 내보내기 기능을 실행하여 생성된 파일을 한컴오피스 한글 프로그램 또는 한글 뷰어로 열었을 때, 본문 내부의 이미지가 보이지 않고 **빈 점선 테두리 상자**로만 렌더링되는 현상.
* HWPX 내부 Zip 압축 구조를 풀어서 확인해보면 이미지 파일 자체(`BinData/BIN0001.png` 등)는 정상적으로 내장되어 있으나, 뷰어가 이를 화면에 그리지 못함.

---

## 2. 원인 분석 (Root Cause)
이미지 바이너리 파일과 본문 문서 요소 간의 **참조 체인(Reference Chain) 오류**가 원인이었습니다.

### 잘못된 설계 (기존 레그레션 패치)
* **오해**: "한글 뷰어는 숫자 형태의 ID(예: `id="0"`)가 필요하다"는 잘못된 전제.
* **잘못된 조치**: 
  1. 그림의 `binaryItemIDRef`를 `"0"`, `"1"` 등 `Contents/header.xml` 내부 `binItem` 순번으로 강제 변환하여 반환.
  2. `Contents/header.xml`에 `binItem` 태그를 생성 및 삽입하여 매핑하려 함.
* **실패 원인**: 실제 한글 프로그램 표준 명세에서 `binaryItemIDRef`는 `Contents/content.hpf` 매니페스트 파일의 `<opf:item id="...">`를 가리켜야 합니다. 뷰어가 존재하지 않는 매핑(숫자 ID)을 찾지 못해 엑박으로 렌더링했습니다.

### 올바른 구조 (표준 한글 HWPX 규격)
1. `Contents/section0.xml` 의 `<hc:img>` 태그 내 **`binaryItemIDRef` 속성은 `Contents/content.hpf` 매니페스트 내의 `<opf:item>`의 `id`와 일치**해야 함 (예: `"BIN0001"`).
2. `Contents/header.xml`에 불필요한 `binItem` 요소를 추가할 필요가 없음.
3. `Contents/content.hpf` 내의 이미지 파일 리소스를 기술하는 `<opf:item>` 항목에 **`isEmbeded="1"`** 속성이 명시적으로 지정되어 있어야 함.

---

## 3. 수정 내용 (Resolution)

`HwpxDocument.add_image` 동작을 오버라이딩하여 아래의 두 단계를 수행합니다:
1. 라이브러리가 반환하는 매니페스트 item ID(예: `"BIN0001"`)를 변형하지 않고 그대로 `binaryItemIDRef`로 사용할 수 있게 반환합니다.
2. HWPX 내부 패키지 매니페스트 구조를 나타내는 `Contents/content.hpf`를 파싱하여, 이미지의 ID와 일치하는 `<opf:item>` 노드를 찾아 `isEmbeded="1"` 속성을 주입하고 동적 저장합니다.

### 참조 체인 관계도
```
[본문 Contents/section0.xml]
<hc:img binaryItemIDRef="BIN0001"/>
       │
       ▼ (ID 매칭 참조)
[매니페스트 Contents/content.hpf]
<opf:item id="BIN0001" href="BinData/BIN0001.png" isEmbeded="1"/>
       │
       ▼ (실제 파일 경로 참조)
[바이너리 리소스]
BinData/BIN0001.png
```

---

## 4. 실제 패치 코드 (Implementation Code)

현재 `biz_guide_app.py` 및 `oracle_guide_app.py`에 공통 적용된 몽키패치 코드 스니펫입니다:

```python
# python-hwpx 보정 패치 (그림 매핑 정보 수정):
# 한글이 직접 저장한 hwpx 기준, section0.xml의 binaryItemIDRef는
# content.hpf의 <opf:item id>를 참조하고 해당 item에 isEmbeded="1"이
# 있어야 뷰어가 그림 바이너리를 로드한다. (header.xml binItem id 무관)
_orig_add_image = HwpxDocument.add_image
def patched_add_image(self, image_data, image_format, *, item_id=None):
    orig_item_id = _orig_add_image(self, image_data, image_format, item_id=item_id)
    try:
        manifest_el = self._package._manifest_element()
        if manifest_el is not None:
            for item in manifest_el:
                if item.tag.endswith('}item') and item.get('id') == orig_item_id:
                    item.set('isEmbeded', '1')
            self._package._persist_manifest()
    except Exception:
        pass
    return orig_item_id
HwpxDocument.add_image = patched_add_image
```

이 규칙을 항상 인지하여 향후 HWPX 문서 출력 생성 코드를 건드릴 때 참조 체인이 회손되지 않도록 주의하십시오.
