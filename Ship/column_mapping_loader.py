from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple


def load_header_rows(csv_path: Path) -> Dict[str, List[str]]:
    """
    Parse 컬럼맵핑.csv which contains 3 lines, each starting with a label and a comma,
    followed by tab-separated header names.
    Returns a dict: { 'shopby': [...], 'cornerlogis': [...], 'sheet1': [...] }
    """
    txt = csv_path.read_text(encoding='utf-8').splitlines()
    result: Dict[str, List[str]] = {"shopby": [], "cornerlogis": [], "sheet1": []}
    for line in txt:
        if not line.strip():
            continue
        if "," in line:
            label, rest = line.split(",", 1)
        else:
            # fallback: no comma, assume whole line is headers
            label, rest = line[:20], line
        headers = [h.strip() for h in rest.split('\t') if h.strip()]
        if "샵바이" in label:
            result["shopby"] = headers
        elif "코너로지스" in label:
            result["cornerlogis"] = headers
        elif "시트1" in label:
            result["sheet1"] = headers
    return result


def build_cornerlogis_mapping(shopby_headers: List[str], corner_headers: List[str]) -> List[Tuple[str, str]]:
    """Heuristic mapping from shopby to cornerlogis headers.
    Returns list of (source, target).
    """
    def has(name: str) -> bool:
        return name in shopby_headers

    mapping: List[Tuple[str, str]] = []
    # 주문번호(고객사) <- 주문번호
    if has("주문번호"):
        mapping.append(("주문번호", "주문번호(고객사)"))
    # 주문자명 <- 수령자명 우선, 없으면 주문자명
    if has("수령자명"):
        mapping.append(("수령자명", "주문자명"))
    elif has("주문자명"):
        mapping.append(("주문자명", "주문자명"))
    # 주문자 연락처 <- 수령자연락처 우선, 없으면 주문자연락처
    if has("수령자연락처"):
        mapping.append(("수령자연락처", "주문자 연락처"))
    elif has("주문자연락처"):
        mapping.append(("주문자연락처", "주문자 연락처"))
    # 우편번호 <- 우편번호
    if has("우편번호"):
        mapping.append(("우편번호", "우편번호"))
    # 배송지 주소 <- 주소
    if has("주소"):
        mapping.append(("주소", "배송지 주소"))
    # 주문금액 <- 실결제금액 우선, 없으면 주문금액
    if has("실결제금액"):
        mapping.append(("실결제금액", "주문금액"))
    elif has("주문금액"):
        mapping.append(("주문금액", "주문금액"))
    # 주문일자 <- 주문일시 우선, 없으면 결제일시
    if has("주문일시"):
        mapping.append(("주문일시", "주문일자"))
    elif has("결제일시"):
        mapping.append(("결제일시", "주문일자"))
    # 상품가격 <- 즉시할인가 우선, 없으면 공급가
    if has("즉시할인가"):
        mapping.append(("즉시할인가", "상품가격"))
    elif has("공급가"):
        mapping.append(("공급가", "상품가격"))
    # 수량 <- 수량
    if has("수량"):
        mapping.append(("수량", "수량"))
    # 비고(배송시 메모) <- 배송메모 우선, 없으면 업무메시지
    if has("배송메모"):
        mapping.append(("배송메모", "비고(배송시 메모)"))
    elif has("업무메시지"):
        mapping.append(("업무메시지", "비고(배송시 메모)"))

    # 코너로지스상품코드는 별도 처리(파이프라인에서 계산/치환 후 컬럼명 제공)
    return mapping


def build_sheet1_mapping(shopby_headers: List[str], sheet1_headers: List[str]) -> List[Tuple[str, str]]:
    """Mapping for Sheet1 append: (source, target) order will follow sheet1 headers.
    We only map what we can. Missing targets will be handled as blanks upstream.
    """
    def has(name: str) -> bool:
        return name in shopby_headers

    mapping: List[Tuple[str, str]] = []
    # No. -> blank (handled upstream)
    # 출고일 -> 배송중처리일시 or 배송완료처리일시; upstream will compute '출고일' column
    # 상품명 <- 상품명
    if has("상품명"):
        mapping.append(("상품명", "상품명"))
    # 상품번호 <- 상품번호
    if has("상품번호"):
        mapping.append(("상품번호", "상품번호"))
    # 링크 -> blank (no direct source)
    # JK 확인 -> blank
    return mapping


