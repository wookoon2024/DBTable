# -*- coding: utf-8 -*-
"""
DB 돋보기 - 샘플 데이터 생성기

가상의 온라인 쇼핑몰 도메인을 기준으로 metadata.db 와 첨부파일 일체를
처음부터 새로 만든다. 실제 업무 데이터는 일절 포함하지 않는다.

사용법:
    python sample_data/build_sample.py
"""
import os
import sqlite3
import shutil
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "metadata.db")
ATTACH_DIR = os.path.join(BASE_DIR, "attachments")

FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"
FONT_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"

NOW = datetime(2026, 7, 20, 9, 0, 0)
NOW_S = NOW.strftime("%Y-%m-%d %H:%M:%S")

SAMPLE_TAG = "본 데이터는 데모용 샘플입니다. 실제 업무 데이터가 아닙니다."


def ts(days_ago=0, hours=0):
    return (NOW - timedelta(days=days_ago, hours=hours)).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- 스키마
SCHEMA = """
CREATE TABLE tables (
    table_name TEXT PRIMARY KEY,
    table_ko_name TEXT,
    task_category TEXT DEFAULT '기타',
    is_favorite INTEGER DEFAULT 0,
    updated_at TEXT
);
CREATE TABLE table_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT,
    task_category TEXT DEFAULT '기타',
    task_order INTEGER DEFAULT 0,
    display_name TEXT,
    joins_json TEXT
);
CREATE TABLE columns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT,
    column_name TEXT,
    column_ko_name TEXT,
    data_type TEXT,
    length INTEGER,
    is_nullable TEXT,
    is_pk TEXT,
    is_selected INTEGER DEFAULT 1,
    is_where INTEGER DEFAULT 0,
    FOREIGN KEY(table_name) REFERENCES tables(table_name) ON DELETE CASCADE,
    UNIQUE(table_name, column_name) ON CONFLICT REPLACE
);
CREATE TABLE relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    src_table_name TEXT,
    src_column_name TEXT,
    ref_table_name TEXT,
    custom_query TEXT,
    UNIQUE(src_table_name, src_column_name) ON CONFLICT REPLACE
);
CREATE TABLE query_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT,
    parent_id INTEGER DEFAULT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TEXT
);
CREATE TABLE queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER,
    query_title TEXT,
    query_content TEXT,
    description TEXT,
    created_at TEXT,
    is_favorite INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY(category_id) REFERENCES query_categories(id) ON DELETE CASCADE
);
CREATE TABLE recent_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_title TEXT,
    query_content TEXT,
    copied_at TEXT
);
CREATE TABLE common_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    column_name TEXT,
    code_group_id TEXT,
    code_group_name TEXT,
    code_value TEXT,
    code_ko_name TEXT,
    description TEXT
);
CREATE TABLE app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE recent_tables (
    table_name TEXT PRIMARY KEY,
    viewed_at TEXT,
    FOREIGN KEY(table_name) REFERENCES tables(table_name) ON DELETE CASCADE
);
CREATE TABLE COMMON_CODE_MASTER (
    CODE_GROUP_VAL TEXT PRIMARY KEY,
    COLUMN_NAME TEXT,
    CODE_GROUP_NAME TEXT,
    USE_YN TEXT,
    OWNER TEXT
);
CREATE TABLE COMMON_CODE_SUB (
    CODE_GROUP_VAL TEXT,
    CODE_VALUE TEXT,
    CODE_NAME TEXT,
    DESCRIPTION TEXT,
    USE_YN TEXT,
    SORT_ORDER INTEGER,
    PRIMARY KEY (CODE_GROUP_VAL, CODE_VALUE)
);
CREATE TABLE task_doc_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT,
    parent_id INTEGER DEFAULT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TEXT
);
CREATE TABLE task_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER,
    title TEXT,
    content TEXT,
    created_at TEXT,
    updated_at TEXT,
    is_favorite INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    is_repeating INTEGER DEFAULT 0,
    recurrence_type TEXT DEFAULT NULL,
    recurrence_value TEXT DEFAULT NULL,
    has_period INTEGER DEFAULT 0,
    start_date TEXT DEFAULT NULL,
    end_date TEXT DEFAULT NULL,
    FOREIGN KEY(category_id) REFERENCES task_doc_categories(id) ON DELETE CASCADE
);
CREATE TABLE task_doc_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER,
    file_path TEXT,
    file_name TEXT,
    file_size INTEGER,
    created_at TEXT,
    is_embed INTEGER DEFAULT 0,
    FOREIGN KEY(doc_id) REFERENCES task_documents(id) ON DELETE CASCADE
);
"""

# ---------------------------------------------------------------- 테이블 정의
# (table_name, 한글명, 업무분류, 즐겨찾기)
TABLES = [
    ("TB_MEMBER",      "회원 기본",      "회원관리", 1),
    ("TB_MEMBER_ADDR", "회원 배송지",    "회원관리", 0),
    ("TB_POINT_HIST",  "포인트 적립/사용 이력", "회원관리", 0),
    ("TB_CATEGORY",    "상품 분류",      "상품관리", 0),
    ("TB_PRODUCT",     "상품 기본",      "상품관리", 1),
    ("TB_PRODUCT_OPT", "상품 옵션",      "상품관리", 0),
    ("TB_ORDER",       "주문 기본",      "주문/결제", 1),
    ("TB_ORDER_ITEM",  "주문 상품",      "주문/결제", 1),
    ("TB_PAYMENT",     "결제 내역",      "주문/결제", 0),
    ("TB_DELIVERY",    "배송 정보",      "배송관리", 0),
    ("TB_CLAIM",       "취소/반품/교환", "배송관리", 0),
]

# table_name -> [(col, 한글, 타입, 길이, nullable, pk, selected, where), ...]
COLUMNS = {
    "TB_MEMBER": [
        ("MEMBER_ID",    "회원 ID",      "VARCHAR2", 20,  "N", "Y", 1, 1),
        ("MEMBER_NM",    "회원명",       "VARCHAR2", 50,  "N", "N", 1, 0),
        ("EMAIL",        "이메일",       "VARCHAR2", 100, "Y", "N", 1, 1),
        ("MOBILE_NO",    "휴대폰번호",   "VARCHAR2", 20,  "Y", "N", 1, 0),
        ("MEMBER_GRADE", "회원등급",     "VARCHAR2", 2,   "N", "N", 1, 1),
        ("MEMBER_STAT",  "회원상태",     "VARCHAR2", 2,   "N", "N", 1, 1),
        ("BIRTH_DT",     "생년월일",     "VARCHAR2", 8,   "Y", "N", 1, 0),
        ("JOIN_DT",      "가입일시",     "DATE",     None, "N", "N", 1, 1),
        ("LAST_LOGIN_DT","최종로그인일시","DATE",    None, "Y", "N", 1, 0),
        ("WITHDRAW_DT",  "탈퇴일시",     "DATE",     None, "Y", "N", 0, 0),
        ("REG_DT",       "등록일시",     "DATE",     None, "N", "N", 0, 0),
        ("UPD_DT",       "수정일시",     "DATE",     None, "Y", "N", 0, 0),
    ],
    "TB_MEMBER_ADDR": [
        ("ADDR_SEQ",    "배송지 일련번호", "NUMBER",   12,  "N", "Y", 1, 0),
        ("MEMBER_ID",   "회원 ID",        "VARCHAR2", 20,  "N", "N", 1, 1),
        ("ADDR_NM",     "배송지명",       "VARCHAR2", 50,  "Y", "N", 1, 0),
        ("RECEIVER_NM", "수령인명",       "VARCHAR2", 50,  "N", "N", 1, 0),
        ("ZIP_CD",      "우편번호",       "VARCHAR2", 6,   "N", "N", 1, 0),
        ("ADDR1",       "기본주소",       "VARCHAR2", 200, "N", "N", 1, 0),
        ("ADDR2",       "상세주소",       "VARCHAR2", 200, "Y", "N", 1, 0),
        ("DEFAULT_YN",  "기본배송지여부", "VARCHAR2", 1,   "N", "N", 1, 1),
        ("REG_DT",      "등록일시",       "DATE",     None, "N", "N", 0, 0),
    ],
    "TB_POINT_HIST": [
        ("POINT_SEQ",  "포인트 일련번호", "NUMBER",   12,  "N", "Y", 1, 0),
        ("MEMBER_ID",  "회원 ID",        "VARCHAR2", 20,  "N", "N", 1, 1),
        ("ORDER_NO",   "주문번호",       "VARCHAR2", 20,  "Y", "N", 1, 1),
        ("POINT_TYPE", "포인트구분",     "VARCHAR2", 2,   "N", "N", 1, 1),
        ("POINT_AMT",  "포인트금액",     "NUMBER",   12,  "N", "N", 1, 0),
        ("BALANCE_AMT","잔여포인트",     "NUMBER",   12,  "N", "N", 1, 0),
        ("EXPIRE_DT",  "소멸예정일",     "DATE",     None, "Y", "N", 1, 0),
        ("REMARK",     "비고",           "VARCHAR2", 200, "Y", "N", 1, 0),
        ("REG_DT",     "등록일시",       "DATE",     None, "N", "N", 1, 1),
    ],
    "TB_CATEGORY": [
        ("CATEGORY_CD",  "분류코드",   "VARCHAR2", 10,  "N", "Y", 1, 1),
        ("CATEGORY_NM",  "분류명",     "VARCHAR2", 100, "N", "N", 1, 0),
        ("PARENT_CD",    "상위분류코드","VARCHAR2", 10, "Y", "N", 1, 1),
        ("DEPTH_NO",     "분류 깊이",  "NUMBER",   2,   "N", "N", 1, 0),
        ("SORT_ORDER",   "정렬순서",   "NUMBER",   4,   "N", "N", 1, 0),
        ("USE_YN",       "사용여부",   "VARCHAR2", 1,   "N", "N", 1, 1),
    ],
    "TB_PRODUCT": [
        ("PRODUCT_CD",   "상품코드",     "VARCHAR2", 20,  "N", "Y", 1, 1),
        ("PRODUCT_NM",   "상품명",       "VARCHAR2", 200, "N", "N", 1, 1),
        ("CATEGORY_CD",  "분류코드",     "VARCHAR2", 10,  "N", "N", 1, 1),
        ("SALE_PRICE",   "판매가",       "NUMBER",   12,  "N", "N", 1, 0),
        ("COST_PRICE",   "원가",         "NUMBER",   12,  "Y", "N", 0, 0),
        ("STOCK_QTY",    "재고수량",     "NUMBER",   8,   "N", "N", 1, 1),
        ("SALE_STAT",    "판매상태",     "VARCHAR2", 2,   "N", "N", 1, 1),
        ("SUPPLIER_NM",  "공급사명",     "VARCHAR2", 100, "Y", "N", 1, 0),
        ("REG_DT",       "등록일시",     "DATE",     None, "N", "N", 0, 0),
        ("UPD_DT",       "수정일시",     "DATE",     None, "Y", "N", 0, 0),
    ],
    "TB_PRODUCT_OPT": [
        ("OPT_SEQ",     "옵션 일련번호", "NUMBER",   12,  "N", "Y", 1, 0),
        ("PRODUCT_CD",  "상품코드",     "VARCHAR2", 20,  "N", "N", 1, 1),
        ("OPT_NM",      "옵션명",       "VARCHAR2", 100, "N", "N", 1, 0),
        ("OPT_VAL",     "옵션값",       "VARCHAR2", 100, "N", "N", 1, 0),
        ("ADD_PRICE",   "추가금액",     "NUMBER",   12,  "N", "N", 1, 0),
        ("OPT_STOCK_QTY","옵션재고수량","NUMBER",   8,   "N", "N", 1, 1),
        ("USE_YN",      "사용여부",     "VARCHAR2", 1,   "N", "N", 1, 1),
    ],
    "TB_ORDER": [
        ("ORDER_NO",     "주문번호",     "VARCHAR2", 20,  "N", "Y", 1, 1),
        ("MEMBER_ID",    "회원 ID",      "VARCHAR2", 20,  "N", "N", 1, 1),
        ("ORDER_DT",     "주문일시",     "DATE",     None, "N", "N", 1, 1),
        ("ORDER_STAT",   "주문상태",     "VARCHAR2", 2,   "N", "N", 1, 1),
        ("TOTAL_AMT",    "주문총액",     "NUMBER",   14,  "N", "N", 1, 0),
        ("DISCOUNT_AMT", "할인금액",     "NUMBER",   14,  "N", "N", 1, 0),
        ("POINT_USE_AMT","포인트사용액", "NUMBER",   12,  "N", "N", 1, 0),
        ("PAY_AMT",      "실결제금액",   "NUMBER",   14,  "N", "N", 1, 0),
        ("ORDERER_NM",   "주문자명",     "VARCHAR2", 50,  "N", "N", 1, 0),
        ("CANCEL_DT",    "취소일시",     "DATE",     None, "Y", "N", 1, 0),
        ("REG_DT",       "등록일시",     "DATE",     None, "N", "N", 0, 0),
    ],
    "TB_ORDER_ITEM": [
        ("ORDER_NO",    "주문번호",     "VARCHAR2", 20,  "N", "Y", 1, 1),
        ("ITEM_SEQ",    "주문상품순번", "NUMBER",   4,   "N", "Y", 1, 0),
        ("PRODUCT_CD",  "상품코드",     "VARCHAR2", 20,  "N", "N", 1, 1),
        ("OPT_SEQ",     "옵션 일련번호","NUMBER",   12,  "Y", "N", 1, 0),
        ("ORDER_QTY",   "주문수량",     "NUMBER",   8,   "N", "N", 1, 0),
        ("UNIT_PRICE",  "단가",         "NUMBER",   12,  "N", "N", 1, 0),
        ("ITEM_AMT",    "상품금액",     "NUMBER",   14,  "N", "N", 1, 0),
        ("ITEM_STAT",   "상품별상태",   "VARCHAR2", 2,   "N", "N", 1, 1),
    ],
    "TB_PAYMENT": [
        ("PAY_NO",      "결제번호",     "VARCHAR2", 20,  "N", "Y", 1, 1),
        ("ORDER_NO",    "주문번호",     "VARCHAR2", 20,  "N", "N", 1, 1),
        ("PAY_METHOD",  "결제수단",     "VARCHAR2", 2,   "N", "N", 1, 1),
        ("PAY_STAT",    "결제상태",     "VARCHAR2", 2,   "N", "N", 1, 1),
        ("PAY_AMT",     "결제금액",     "NUMBER",   14,  "N", "N", 1, 0),
        ("PG_TID",      "PG 거래번호",  "VARCHAR2", 50,  "Y", "N", 1, 1),
        ("APPROVE_DT",  "승인일시",     "DATE",     None, "Y", "N", 1, 1),
        ("CANCEL_DT",   "취소일시",     "DATE",     None, "Y", "N", 1, 0),
    ],
    "TB_DELIVERY": [
        ("DELIVERY_NO", "배송번호",     "VARCHAR2", 20,  "N", "Y", 1, 1),
        ("ORDER_NO",    "주문번호",     "VARCHAR2", 20,  "N", "N", 1, 1),
        ("DELIVERY_STAT","배송상태",    "VARCHAR2", 2,   "N", "N", 1, 1),
        ("CARRIER_CD",  "택배사코드",   "VARCHAR2", 10,  "Y", "N", 1, 1),
        ("INVOICE_NO",  "송장번호",     "VARCHAR2", 30,  "Y", "N", 1, 1),
        ("RECEIVER_NM", "수령인명",     "VARCHAR2", 50,  "N", "N", 1, 0),
        ("SEND_DT",     "발송일시",     "DATE",     None, "Y", "N", 1, 0),
        ("COMPLETE_DT", "배송완료일시", "DATE",     None, "Y", "N", 1, 0),
    ],
    "TB_CLAIM": [
        ("CLAIM_NO",    "클레임번호",   "VARCHAR2", 20,  "N", "Y", 1, 1),
        ("ORDER_NO",    "주문번호",     "VARCHAR2", 20,  "N", "N", 1, 1),
        ("ITEM_SEQ",    "주문상품순번", "NUMBER",   4,   "N", "N", 1, 0),
        ("CLAIM_TYPE",  "클레임구분",   "VARCHAR2", 2,   "N", "N", 1, 1),
        ("CLAIM_STAT",  "처리상태",     "VARCHAR2", 2,   "N", "N", 1, 1),
        ("CLAIM_REASON","사유코드",     "VARCHAR2", 4,   "Y", "N", 1, 0),
        ("REFUND_AMT",  "환불금액",     "NUMBER",   14,  "Y", "N", 1, 0),
        ("REQ_DT",      "접수일시",     "DATE",     None, "N", "N", 1, 1),
        ("COMPLETE_DT", "처리완료일시", "DATE",     None, "Y", "N", 1, 0),
    ],
}

# (src_table, src_column, ref_table)
RELATIONS = [
    ("TB_MEMBER_ADDR", "MEMBER_ID",   "TB_MEMBER"),
    ("TB_POINT_HIST",  "MEMBER_ID",   "TB_MEMBER"),
    ("TB_POINT_HIST",  "ORDER_NO",    "TB_ORDER"),
    ("TB_PRODUCT",     "CATEGORY_CD", "TB_CATEGORY"),
    ("TB_CATEGORY",    "PARENT_CD",   "TB_CATEGORY"),
    ("TB_PRODUCT_OPT", "PRODUCT_CD",  "TB_PRODUCT"),
    ("TB_ORDER",       "MEMBER_ID",   "TB_MEMBER"),
    ("TB_ORDER_ITEM",  "ORDER_NO",    "TB_ORDER"),
    ("TB_ORDER_ITEM",  "PRODUCT_CD",  "TB_PRODUCT"),
    ("TB_ORDER_ITEM",  "OPT_SEQ",     "TB_PRODUCT_OPT"),
    ("TB_PAYMENT",     "ORDER_NO",    "TB_ORDER"),
    ("TB_DELIVERY",    "ORDER_NO",    "TB_ORDER"),
    ("TB_CLAIM",       "ORDER_NO",    "TB_ORDER"),
]

# ---------------------------------------------------------------- 공통코드
# (group_id, column_name, group_name, [(value, name, desc), ...])
CODE_GROUPS = [
    ("ORDER_STAT_GRP", "ORDER_STAT", "주문상태그룹", [
        ("10", "주문접수",   "주문서가 정상 생성된 상태"),
        ("20", "결제완료",   "PG 승인이 완료된 상태"),
        ("30", "상품준비중", "출고 대기 상태"),
        ("40", "배송중",     "택배사 인계 완료"),
        ("50", "배송완료",   "수령 확인 완료"),
        ("90", "주문취소",   "결제 취소까지 완료된 상태"),
    ]),
    ("PAY_METHOD_GRP", "PAY_METHOD", "결제수단그룹", [
        ("01", "신용카드",     "PG 카드 결제"),
        ("02", "계좌이체",     "실시간 계좌이체"),
        ("03", "가상계좌",     "입금 대기 후 확정"),
        ("04", "간편결제",     "간편결제 대행사 경유"),
        ("05", "포인트전액",   "포인트로 전액 결제"),
    ]),
    ("PAY_STAT_GRP", "PAY_STAT", "결제상태그룹", [
        ("10", "승인대기", "PG 요청 후 응답 대기"),
        ("20", "승인완료", "정상 승인"),
        ("30", "부분취소", "일부 금액 취소"),
        ("40", "전체취소", "전액 취소"),
        ("90", "승인실패", "PG 오류 또는 한도 초과"),
    ]),
    ("MEMBER_GRADE_GRP", "MEMBER_GRADE", "회원등급그룹", [
        ("01", "일반",     "기본 등급"),
        ("02", "실버",     "연 30만원 이상 구매"),
        ("03", "골드",     "연 100만원 이상 구매"),
        ("04", "VIP",      "연 300만원 이상 구매"),
    ]),
    ("MEMBER_STAT_GRP", "MEMBER_STAT", "회원상태그룹", [
        ("10", "정상",     "로그인 및 구매 가능"),
        ("20", "휴면",     "1년 이상 미접속"),
        ("30", "정지",     "관리자에 의한 이용 정지"),
        ("90", "탈퇴",     "탈퇴 처리 완료"),
    ]),
    ("DELIVERY_STAT_GRP", "DELIVERY_STAT", "배송상태그룹", [
        ("10", "배송준비", "송장 미발행"),
        ("20", "집화완료", "택배사 집화"),
        ("30", "배송중",   "간선 상차 이후"),
        ("40", "배송완료", "수령 완료"),
        ("90", "배송실패", "주소 불명 등"),
    ]),
    ("CLAIM_TYPE_GRP", "CLAIM_TYPE", "클레임구분그룹", [
        ("01", "취소", "출고 전 주문 취소"),
        ("02", "반품", "수령 후 반송"),
        ("03", "교환", "동일 상품 재발송"),
    ]),
    ("POINT_TYPE_GRP", "POINT_TYPE", "포인트구분그룹", [
        ("01", "구매적립", "주문 확정 시 적립"),
        ("02", "사용",     "주문 시 차감"),
        ("03", "소멸",     "유효기간 만료"),
        ("04", "관리자지급", "보상/이벤트 지급"),
    ]),
]

SAMPLE_OWNER = "SHOPDB"

# ---------------------------------------------------------------- 쿼리정보
# 최상위 카테고리 -> 하위 카테고리 -> 쿼리 목록
# 쿼리: (제목, SQL, 설명, 즐겨찾기)
QUERY_TREE = [
    ("주문/결제 조회", [
        ("일별 매출 집계", [
            ("일자별 주문/매출 집계",
             """SELECT TO_CHAR(O.ORDER_DT, 'YYYY-MM-DD') AS ORDER_YMD
     , COUNT(DISTINCT O.ORDER_NO)      AS ORDER_CNT
     , SUM(O.PAY_AMT)                  AS PAY_AMT
     , ROUND(AVG(O.PAY_AMT))           AS AVG_AMT
  FROM TB_ORDER O
 WHERE O.ORDER_DT >= TRUNC(SYSDATE) - 30
   AND O.ORDER_STAT <> '90'
 GROUP BY TO_CHAR(O.ORDER_DT, 'YYYY-MM-DD')
 ORDER BY 1 DESC;""",
             "최근 30일간 일자별 주문 건수와 실결제 금액을 집계한다. 취소 주문(90)은 제외.", 1),

            ("결제수단별 매출 비중",
             """SELECT P.PAY_METHOD
     , C.CODE_NAME                     AS PAY_METHOD_NM
     , COUNT(*)                        AS PAY_CNT
     , SUM(P.PAY_AMT)                  AS PAY_AMT
     , ROUND(RATIO_TO_REPORT(SUM(P.PAY_AMT)) OVER () * 100, 2) AS PCT
  FROM TB_PAYMENT P
  LEFT JOIN COMMON_CODE_SUB C
    ON C.CODE_GROUP_VAL = 'PAY_METHOD_GRP'
   AND C.CODE_VALUE     = P.PAY_METHOD
 WHERE P.PAY_STAT = '20'
   AND P.APPROVE_DT >= TRUNC(SYSDATE, 'MM')
 GROUP BY P.PAY_METHOD, C.CODE_NAME
 ORDER BY PAY_AMT DESC;""",
             "당월 승인 완료 건을 결제수단별로 집계하고 비중(%)까지 산출한다.", 0),

            ("월별 신규회원 대비 첫 구매 전환율",
             """SELECT TO_CHAR(M.JOIN_DT, 'YYYY-MM')  AS JOIN_YM
     , COUNT(*)                         AS JOIN_CNT
     , COUNT(O.MEMBER_ID)               AS BUY_CNT
     , ROUND(COUNT(O.MEMBER_ID) / COUNT(*) * 100, 1) AS CVR
  FROM TB_MEMBER M
  LEFT JOIN (SELECT DISTINCT MEMBER_ID FROM TB_ORDER WHERE ORDER_STAT <> '90') O
    ON O.MEMBER_ID = M.MEMBER_ID
 WHERE M.JOIN_DT >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
 GROUP BY TO_CHAR(M.JOIN_DT, 'YYYY-MM')
 ORDER BY 1;""",
             "최근 6개월 가입자 중 실제 구매까지 이어진 비율을 월 단위로 본다.", 0),
        ]),
        ("이상 주문 점검", [
            ("결제완료 후 24시간 경과 미출고 주문",
             """SELECT O.ORDER_NO
     , O.MEMBER_ID
     , O.ORDER_DT
     , O.PAY_AMT
     , ROUND((SYSDATE - O.ORDER_DT) * 24, 1) AS ELAPSED_HOUR
  FROM TB_ORDER O
 WHERE O.ORDER_STAT = '20'
   AND O.ORDER_DT < SYSDATE - 1
   AND NOT EXISTS (SELECT 1
                     FROM TB_DELIVERY D
                    WHERE D.ORDER_NO = O.ORDER_NO
                      AND D.INVOICE_NO IS NOT NULL)
 ORDER BY O.ORDER_DT;""",
             "결제는 끝났는데 송장이 안 붙은 주문. CS 인입 전에 매일 오전 확인한다.", 1),

            ("주문금액과 결제금액 불일치 건",
             """SELECT O.ORDER_NO
     , O.PAY_AMT                        AS ORDER_PAY_AMT
     , NVL(SUM(P.PAY_AMT), 0)           AS REAL_PAY_AMT
     , O.PAY_AMT - NVL(SUM(P.PAY_AMT), 0) AS DIFF_AMT
  FROM TB_ORDER O
  LEFT JOIN TB_PAYMENT P
    ON P.ORDER_NO = O.ORDER_NO
   AND P.PAY_STAT = '20'
 WHERE O.ORDER_DT >= TRUNC(SYSDATE) - 7
   AND O.ORDER_STAT NOT IN ('90')
 GROUP BY O.ORDER_NO, O.PAY_AMT
HAVING O.PAY_AMT <> NVL(SUM(P.PAY_AMT), 0);""",
             "정산 전 반드시 0건이어야 하는 쿼리. 1건이라도 나오면 PG 대사 필요.", 1),

            ("고아 주문상품 (주문 마스터 없음)",
             """SELECT I.ORDER_NO, I.ITEM_SEQ, I.PRODUCT_CD, I.ITEM_AMT
  FROM TB_ORDER_ITEM I
 WHERE NOT EXISTS (SELECT 1 FROM TB_ORDER O WHERE O.ORDER_NO = I.ORDER_NO);""",
             "배치 중단 등으로 발생할 수 있는 정합성 오류를 잡는다.", 0),
        ]),
    ]),
    ("회원 관리", [
        ("회원 현황", [
            ("등급별 회원 수 및 구매 실적",
             """SELECT M.MEMBER_GRADE
     , C.CODE_NAME                      AS GRADE_NM
     , COUNT(DISTINCT M.MEMBER_ID)      AS MEMBER_CNT
     , NVL(SUM(O.PAY_AMT), 0)           AS TOTAL_AMT
  FROM TB_MEMBER M
  LEFT JOIN COMMON_CODE_SUB C
    ON C.CODE_GROUP_VAL = 'MEMBER_GRADE_GRP'
   AND C.CODE_VALUE     = M.MEMBER_GRADE
  LEFT JOIN TB_ORDER O
    ON O.MEMBER_ID  = M.MEMBER_ID
   AND O.ORDER_STAT <> '90'
 WHERE M.MEMBER_STAT = '10'
 GROUP BY M.MEMBER_GRADE, C.CODE_NAME
 ORDER BY M.MEMBER_GRADE;""",
             "정상 회원만 대상으로 등급별 인원과 누적 구매액을 본다.", 0),

            ("휴면 전환 대상 조회 (1년 미접속)",
             """SELECT M.MEMBER_ID
     , M.MEMBER_NM
     , M.EMAIL
     , M.LAST_LOGIN_DT
     , TRUNC(SYSDATE - M.LAST_LOGIN_DT) AS IDLE_DAYS
  FROM TB_MEMBER M
 WHERE M.MEMBER_STAT = '10'
   AND M.LAST_LOGIN_DT < ADD_MONTHS(SYSDATE, -12)
 ORDER BY M.LAST_LOGIN_DT;""",
             "휴면 전환 배치 대상. 전환 30일 전 사전 안내 메일이 나가야 한다.", 1),
        ]),
        ("포인트", [
            ("회원별 포인트 잔액 검증",
             """SELECT H.MEMBER_ID
     , SUM(CASE WHEN H.POINT_TYPE IN ('01','04') THEN H.POINT_AMT
                ELSE -H.POINT_AMT END)  AS CALC_BALANCE
     , MAX(H.BALANCE_AMT) KEEP (DENSE_RANK LAST ORDER BY H.REG_DT, H.POINT_SEQ) AS LAST_BALANCE
  FROM TB_POINT_HIST H
 GROUP BY H.MEMBER_ID
HAVING SUM(CASE WHEN H.POINT_TYPE IN ('01','04') THEN H.POINT_AMT
                ELSE -H.POINT_AMT END)
       <> MAX(H.BALANCE_AMT) KEEP (DENSE_RANK LAST ORDER BY H.REG_DT, H.POINT_SEQ);""",
             "이력 합계와 최종 잔액이 어긋난 회원을 찾는다. 월 1회 점검 항목.", 0),

            ("30일 내 소멸 예정 포인트",
             """SELECT H.MEMBER_ID
     , SUM(H.POINT_AMT)                 AS EXPIRE_AMT
     , MIN(H.EXPIRE_DT)                 AS FIRST_EXPIRE_DT
  FROM TB_POINT_HIST H
 WHERE H.POINT_TYPE = '01'
   AND H.EXPIRE_DT BETWEEN TRUNC(SYSDATE) AND TRUNC(SYSDATE) + 30
 GROUP BY H.MEMBER_ID
HAVING SUM(H.POINT_AMT) > 0
 ORDER BY EXPIRE_AMT DESC;""",
             "소멸 예정 안내 발송용. 마케팅팀에 매주 월요일 전달.", 0),
        ]),
    ]),
    ("상품/재고", [
        ("재고 점검", [
            ("품절 임박 상품 (재고 10개 이하)",
             """SELECT P.PRODUCT_CD
     , P.PRODUCT_NM
     , C.CATEGORY_NM
     , P.STOCK_QTY
     , P.SUPPLIER_NM
  FROM TB_PRODUCT P
  LEFT JOIN TB_CATEGORY C ON C.CATEGORY_CD = P.CATEGORY_CD
 WHERE P.SALE_STAT = '10'
   AND P.STOCK_QTY <= 10
 ORDER BY P.STOCK_QTY, P.PRODUCT_NM;""",
             "판매중 상품 기준 재고 10개 이하. 발주 담당자 일일 확인 대상.", 1),

            ("옵션 재고와 상품 재고 불일치",
             """SELECT P.PRODUCT_CD
     , P.PRODUCT_NM
     , P.STOCK_QTY                      AS PRODUCT_STOCK
     , NVL(SUM(O.OPT_STOCK_QTY), 0)     AS OPT_STOCK_SUM
  FROM TB_PRODUCT P
  LEFT JOIN TB_PRODUCT_OPT O
    ON O.PRODUCT_CD = P.PRODUCT_CD
   AND O.USE_YN     = 'Y'
 GROUP BY P.PRODUCT_CD, P.PRODUCT_NM, P.STOCK_QTY
HAVING P.STOCK_QTY <> NVL(SUM(O.OPT_STOCK_QTY), 0);""",
             "옵션이 있는 상품은 옵션 재고 합계가 상품 재고와 같아야 한다.", 0),

            ("최근 90일 무판매 상품",
             """SELECT P.PRODUCT_CD, P.PRODUCT_NM, P.SALE_PRICE, P.STOCK_QTY
  FROM TB_PRODUCT P
 WHERE P.SALE_STAT = '10'
   AND NOT EXISTS (SELECT 1
                     FROM TB_ORDER_ITEM I
                     JOIN TB_ORDER O ON O.ORDER_NO = I.ORDER_NO
                    WHERE I.PRODUCT_CD = P.PRODUCT_CD
                      AND O.ORDER_DT  >= SYSDATE - 90)
 ORDER BY P.STOCK_QTY DESC;""",
             "재고는 있는데 안 팔리는 상품. 분기 상품 정리 회의 자료.", 0),
        ]),
    ]),
    ("운영/관리 DML", [
        ("데이터 보정", [
            ("주문 상태 수동 보정",
             """-- 반드시 SELECT 로 대상 확인 후 실행할 것
UPDATE TB_ORDER
   SET ORDER_STAT = :NEW_STAT
     , UPD_DT     = SYSDATE
 WHERE ORDER_NO   = :ORDER_NO
   AND ORDER_STAT = :OLD_STAT;

-- 반영 건수 확인 후 COMMIT
-- ROLLBACK;""",
             "배치 오류로 상태가 멈춘 주문을 보정한다. OLD_STAT 조건 필수.", 0),

            ("휴면 회원 일괄 전환",
             """UPDATE TB_MEMBER
   SET MEMBER_STAT = '20'
     , UPD_DT      = SYSDATE
 WHERE MEMBER_STAT = '10'
   AND LAST_LOGIN_DT < ADD_MONTHS(SYSDATE, -12);

COMMIT;""",
             "휴면 전환 배치가 실패했을 때 수동으로 돌리는 문장.", 0),

            ("테스트 회원 초기화",
             """DELETE FROM TB_POINT_HIST WHERE MEMBER_ID LIKE 'TEST%';
DELETE FROM TB_MEMBER_ADDR WHERE MEMBER_ID LIKE 'TEST%';
DELETE FROM TB_MEMBER      WHERE MEMBER_ID LIKE 'TEST%';

COMMIT;""",
             "개발 DB 전용. 운영에서는 절대 실행 금지.", 0),
        ]),
        ("오라클 딕셔너리", [
            ("스키마 테이블 목록",
             """SELECT T.TABLE_NAME
     , C.COMMENTS                       AS TABLE_COMMENT
     , T.NUM_ROWS
     , T.LAST_ANALYZED
  FROM ALL_TABLES T
  LEFT JOIN ALL_TAB_COMMENTS C
    ON C.OWNER = T.OWNER AND C.TABLE_NAME = T.TABLE_NAME
 WHERE T.OWNER = 'SHOPDB'
 ORDER BY T.TABLE_NAME;""",
             "소유자 기준 테이블 목록과 주석, 통계 정보를 함께 본다.", 0),

            ("컬럼 정의 조회",
             """SELECT C.TABLE_NAME
     , C.COLUMN_ID
     , C.COLUMN_NAME
     , M.COMMENTS                       AS COLUMN_COMMENT
     , C.DATA_TYPE
     , C.DATA_LENGTH
     , C.NULLABLE
  FROM ALL_TAB_COLUMNS C
  LEFT JOIN ALL_COL_COMMENTS M
    ON M.OWNER = C.OWNER
   AND M.TABLE_NAME  = C.TABLE_NAME
   AND M.COLUMN_NAME = C.COLUMN_NAME
 WHERE C.OWNER      = 'SHOPDB'
   AND C.TABLE_NAME = :TABLE_NAME
 ORDER BY C.COLUMN_ID;""",
             "명세표 임포트 시 사용하는 기본 쿼리.", 1),

            ("현재 락 대기 세션 확인",
             """SELECT S.SID
     , S.SERIAL#
     , S.USERNAME
     , S.STATUS
     , S.BLOCKING_SESSION
     , Q.SQL_TEXT
  FROM V$SESSION S
  LEFT JOIN V$SQL Q ON Q.SQL_ID = S.SQL_ID
 WHERE S.BLOCKING_SESSION IS NOT NULL
 ORDER BY S.BLOCKING_SESSION;""",
             "배치 지연 시 가장 먼저 확인하는 쿼리.", 0),
        ]),
    ]),
]

# 최근 복사한 쿼리 이력
RECENT_QUERIES = [
    ("일자별 주문/매출 집계", "SELECT TO_CHAR(O.ORDER_DT, 'YYYY-MM-DD') ...", ts(0, 2)),
    ("품절 임박 상품 (재고 10개 이하)", "SELECT P.PRODUCT_CD, P.PRODUCT_NM ...", ts(0, 5)),
    ("결제완료 후 24시간 경과 미출고 주문", "SELECT O.ORDER_NO, O.MEMBER_ID ...", ts(1)),
    ("컬럼 정의 조회", "SELECT C.TABLE_NAME, C.COLUMN_ID ...", ts(2)),
]

RECENT_TABLES = [
    ("TB_ORDER", ts(0, 1)),
    ("TB_ORDER_ITEM", ts(0, 3)),
    ("TB_MEMBER", ts(1)),
    ("TB_PRODUCT", ts(2)),
    ("TB_PAYMENT", ts(3)),
]


# ---------------------------------------------------------------- 이미지 생성
PALETTE = {
    "bg":     (247, 249, 252),
    "box":    (255, 255, 255),
    "line":   (108, 122, 137),
    "accent": (44, 108, 191),
    "accent2": (36, 150, 118),
    "warn":   (200, 78, 52),
    "text":   (33, 41, 48),
    "muted":  (120, 130, 140),
}


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_PATH, size)


def _center(draw, box, text, f, fill):
    x0, y0, x1, y1 = box
    tb = draw.textbbox((0, 0), text, font=f)
    w, h = tb[2] - tb[0], tb[3] - tb[1]
    draw.text((x0 + (x1 - x0 - w) / 2 - tb[0],
               y0 + (y1 - y0 - h) / 2 - tb[1]), text, font=f, fill=fill)


def new_canvas(w, h, title):
    img = Image.new("RGB", (w, h), PALETTE["bg"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 52], fill=PALETTE["accent"])
    d.text((22, 15), title, font=font(19, True), fill=(255, 255, 255))
    # 샘플 표식
    tag = "SAMPLE"
    f = font(13, True)
    tb = d.textbbox((0, 0), tag, font=f)
    d.rectangle([w - (tb[2] - tb[0]) - 40, 15, w - 18, 37],
                outline=(255, 255, 255), width=1)
    d.text((w - (tb[2] - tb[0]) - 29, 18), tag, font=f, fill=(255, 255, 255))
    return img, d


def box(d, x, y, w, h, label, sub=None, color=None, radius=8):
    color = color or PALETTE["accent"]
    d.rounded_rectangle([x, y, x + w, y + h], radius=radius,
                        fill=PALETTE["box"], outline=color, width=2)
    if sub:
        _center(d, (x, y + 6, x + w, y + h // 2 + 6), label, font(15, True), PALETTE["text"])
        _center(d, (x, y + h // 2, x + w, y + h - 6), sub, font(12), PALETTE["muted"])
    else:
        _center(d, (x, y, x + w, y + h), label, font(15, True), PALETTE["text"])


def arrow(d, x1, y1, x2, y2, label=None, color=None, lx=6, ly=-18):
    color = color or PALETTE["line"]
    d.line([x1, y1, x2, y2], fill=color, width=2)
    # 화살촉
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    for s in (-0.4, 0.4):
        d.line([x2, y2,
                x2 - 11 * math.cos(ang + s), y2 - 11 * math.sin(ang + s)],
               fill=color, width=2)
    if label:
        d.text(((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly), label,
               font=font(12), fill=PALETTE["muted"])


def watermark(img, d):
    w, h = img.size
    d.text((14, h - 22), "※ " + SAMPLE_TAG, font=font(12), fill=PALETTE["muted"])


def img_order_cancel_flow(path):
    img, d = new_canvas(880, 430, "주문 취소 처리 흐름")
    box(d, 40, 90, 170, 62, "취소 요청", "고객/상담사")
    box(d, 250, 90, 170, 62, "출고 여부 확인", "TB_DELIVERY")
    box(d, 460, 30, 170, 62, "즉시 취소", "출고 전", PALETTE["accent2"])
    box(d, 460, 150, 170, 62, "반품 전환", "출고 후", PALETTE["warn"])
    box(d, 670, 90, 170, 62, "PG 결제 취소", "TB_PAYMENT")
    box(d, 460, 265, 170, 62, "회수 완료 확인", "택배사 연동")
    box(d, 250, 265, 170, 62, "포인트 원복", "TB_POINT_HIST")
    box(d, 40, 265, 170, 62, "정산 반영", "익일 배치")

    arrow(d, 210, 121, 250, 121)
    arrow(d, 420, 110, 460, 70, "미출고", lx=-46, ly=-22)
    arrow(d, 420, 132, 460, 172, "출고됨", lx=-46, ly=8)
    arrow(d, 630, 61, 670, 105)
    arrow(d, 630, 181, 670, 137)
    arrow(d, 545, 212, 545, 265)
    arrow(d, 460, 296, 420, 296)
    arrow(d, 250, 296, 210, 296)
    d.text((40, 360), "· 출고 이후 요청은 반드시 반품(02)으로 전환되어야 하며, 즉시 취소로 처리하면 재고가 어긋난다.",
           font=font(13), fill=PALETTE["text"])
    d.text((40, 384), "· PG 취소 실패 시 CLAIM_STAT 을 보류로 두고 재시도 배치가 처리한다.",
           font=font(13), fill=PALETTE["text"])
    watermark(img, d)
    img.save(path)


def img_settlement_process(path):
    img, d = new_canvas(880, 380, "정산 마감 프로세스 (월 1회)")
    steps = [
        ("1. 대사 추출", "PG 원장 수신"),
        ("2. 불일치 검증", "0건 필수"),
        ("3. 수수료 계산", "결제수단별"),
        ("4. 정산서 생성", "공급사 단위"),
        ("5. 승인/전송", "재무팀"),
    ]
    x = 30
    for i, (t, s) in enumerate(steps):
        c = PALETTE["warn"] if i == 1 else PALETTE["accent"]
        box(d, x, 100, 150, 66, t, s, c)
        if i < len(steps) - 1:
            arrow(d, x + 150, 133, x + 172, 133)
        x += 172
    d.rounded_rectangle([30, 210, 850, 300], radius=8,
                        fill=(255, 250, 240), outline=PALETTE["warn"], width=2)
    d.text((48, 226), "마감 전 필수 확인", font=font(15, True), fill=PALETTE["warn"])
    d.text((48, 252), "· '주문금액과 결제금액 불일치 건' 쿼리 결과가 0건인지 반드시 확인한다.",
           font=font(13), fill=PALETTE["text"])
    d.text((48, 274), "· 전월 미처리 클레임(CLAIM_STAT <> 완료)이 남아 있으면 재무팀과 협의 후 이월한다.",
           font=font(13), fill=PALETTE["text"])
    watermark(img, d)
    img.save(path)


def img_erd_order(path):
    """TB_ORDER 를 중심에 둔 3x3 배치. 연결선이 다른 박스를 통과하지 않는다."""
    img, d = new_canvas(880, 470, "주문 도메인 ERD")
    box(d, 60,  75, 180, 60, "TB_MEMBER",     "회원 기본",     PALETTE["accent2"])
    box(d, 350, 75, 180, 60, "TB_PAYMENT",    "결제 내역")
    box(d, 640, 75, 180, 60, "TB_DELIVERY",   "배송 정보")
    box(d, 60,  205, 180, 60, "TB_POINT_HIST", "포인트 이력")
    box(d, 350, 205, 180, 60, "TB_ORDER",      "주문 기본",    PALETTE["accent"])
    box(d, 640, 205, 180, 60, "TB_CLAIM",      "취소/반품/교환")
    box(d, 350, 335, 180, 60, "TB_ORDER_ITEM", "주문 상품",    PALETTE["accent"])
    box(d, 640, 335, 180, 60, "TB_PRODUCT",    "상품 기본",    PALETTE["accent2"])

    # 회원 → 주문
    arrow(d, 240, 128, 348, 208, "1:N", lx=-52, ly=-4)
    # 주문 → 결제
    arrow(d, 440, 203, 440, 139, "1:N", lx=8, ly=-8)
    # 주문 → 배송
    arrow(d, 532, 208, 640, 128, "1:1", lx=4, ly=-6)
    # 주문 → 포인트이력
    arrow(d, 348, 235, 240, 235, "1:N", lx=-14, ly=-22)
    # 주문 → 클레임
    arrow(d, 532, 235, 640, 235, "1:N", lx=-14, ly=-22)
    # 주문 → 주문상품
    arrow(d, 440, 267, 440, 333, "1:N", lx=8, ly=-10)
    # 상품 → 주문상품
    arrow(d, 638, 365, 532, 365, "N:1", lx=-14, ly=-22)
    watermark(img, d)
    img.save(path)


def img_error_screen(path):
    img, d = new_canvas(880, 400, "장애 화면 예시 - 결제 승인 지연")
    d.rounded_rectangle([30, 80, 850, 300], radius=6,
                        fill=(28, 32, 38), outline=PALETTE["line"], width=1)
    lines = [
        ("2026-07-19 14:22:07 [ERROR] PaymentApprovalJob", (255, 120, 100)),
        ("  org.springframework.web.client.ResourceAccessException:", (230, 230, 230)),
        ("    I/O error on POST request for \"https://pg.example-sample.co.kr/approve\":", (200, 200, 200)),
        ("    Read timed out (connect=3000ms, read=5000ms)", (200, 200, 200)),
        ("  → ORDER_NO=SO20260719000841  PAY_NO=PY20260719000915", (255, 210, 120)),
        ("  → 재시도 3회 실패, PAY_STAT 을 '10'(승인대기)로 유지", (255, 210, 120)),
        ("2026-07-19 14:22:12 [WARN ] 승인대기 누적 건수 = 47", (255, 180, 90)),
    ]
    y = 100
    for t, c in lines:
        d.text((48, y), t, font=font(13), fill=c)
        y += 26
    d.text((30, 320), "1차 조치: PG 상태페이지 확인 → 승인대기 건수 추이 확인 → 5분 내 회복 없으면 결제수단 전환 공지",
           font=font(13), fill=PALETTE["text"])
    d.text((30, 344), "에스컬레이션: 승인대기 100건 초과 또는 10분 경과 시 결제팀 리드 호출",
           font=font(13), fill=PALETTE["warn"])
    watermark(img, d)
    img.save(path)


def img_deploy_board(path):
    img, d = new_canvas(880, 450, "정기 배포 체크 보드")
    cols = ["항목", "담당", "상태"]
    rows = [
        ("DB 스키마 변경 스크립트 리뷰", "DBA", "완료"),
        ("배치 중단 및 스케줄 해제", "운영", "완료"),
        ("애플리케이션 배포 (WAS 2대 순차)", "개발", "진행중"),
        ("공통코드 캐시 초기화", "개발", "대기"),
        ("스모크 테스트 (주문 → 결제 → 배송)", "QA", "대기"),
        ("배치 스케줄 재등록", "운영", "대기"),
    ]
    x0, y0, w0 = 30, 90, 820
    d.rectangle([x0, y0, x0 + w0, y0 + 36], fill=PALETTE["accent"])
    for cx, c in zip([50, 560, 700], cols):
        d.text((cx, y0 + 9), c, font=font(14, True), fill=(255, 255, 255))
    y = y0 + 36
    stat_color = {"완료": PALETTE["accent2"], "진행중": (214, 148, 30), "대기": PALETTE["muted"]}
    for i, (t, o, s) in enumerate(rows):
        bg = (255, 255, 255) if i % 2 == 0 else (243, 246, 250)
        d.rectangle([x0, y, x0 + w0, y + 40], fill=bg, outline=(226, 231, 237))
        d.text((50, y + 12), t, font=font(14), fill=PALETTE["text"])
        d.text((560, y + 12), o, font=font(14), fill=PALETTE["muted"])
        d.text((700, y + 12), s, font=font(14, True), fill=stat_color[s])
        y += 40
    d.text((30, y + 16), "롤백 기준: 스모크 테스트 실패 또는 주문 생성 오류율 1% 초과 시 즉시 이전 빌드로 복귀",
           font=font(13), fill=PALETTE["warn"])
    watermark(img, d)
    img.save(path)


def img_dev_env(path):
    img, d = new_canvas(880, 360, "로컬 개발 환경 구성")
    box(d, 40, 100, 180, 70, "개발 PC", "IDE + JDK 17", PALETTE["accent2"])
    box(d, 280, 100, 180, 70, "로컬 WAS", "localhost:8080")
    box(d, 520, 60, 180, 70, "개발 DB", "Oracle 19c", PALETTE["accent"])
    box(d, 520, 175, 180, 70, "DB 돋보기", "테이블 명세 조회", PALETTE["accent"])
    arrow(d, 220, 135, 280, 135)
    arrow(d, 460, 125, 520, 95, "JDBC")
    arrow(d, 220, 155, 520, 210, "명세 참조")
    d.text((40, 270), "· 개발 DB 접속 정보는 사내 위키의 '개발환경' 문서를 참고한다. (샘플 환경에서는 제공되지 않음)",
           font=font(13), fill=PALETTE["text"])
    d.text((40, 294), "· 운영 DB 직접 접속은 금지되어 있으며, 조회가 필요하면 DBA에게 요청한다.",
           font=font(13), fill=PALETTE["text"])
    watermark(img, d)
    img.save(path)


# ---------------------------------------------------------------- 업무정보 본문
NOTICE = (
    '<table width="100%" cellpadding="10" cellspacing="0" '
    'style="background-color:#fff6e5;border:1px solid #e0a94a;"><tr><td>'
    '<span style="color:#9a5b00;"><b>[샘플 데이터]</b> ' + SAMPLE_TAG +
    ' 등장하는 회사·담당자·시스템명은 모두 가상입니다.</span>'
    '</td></tr></table><br>'
)


def h(title, lead, body):
    return (f'{NOTICE}<h2 style="color:#2c6cbf;">{title}</h2>'
            f'<p style="color:#556;">{lead}</p>{body}')


def tbl(headers, rows):
    out = ['<table border="1" cellpadding="6" cellspacing="0" '
           'width="100%" style="border-collapse:collapse;">']
    out.append('<tr style="background-color:#eef3fa;">' +
               "".join(f'<th align="left">{c}</th>' for c in headers) + '</tr>')
    for r in rows:
        out.append('<tr>' + "".join(f'<td>{c}</td>' for c in r) + '</tr>')
    out.append('</table>')
    return "".join(out)


DOC_INTRO = h(
    "DB 돋보기 샘플 데이터 안내",
    "이 저장소에 포함된 metadata.db 는 기능 시연을 위해 생성된 가상 데이터입니다.",
    "<h3>무엇이 들어 있나</h3>" +
    tbl(["구분", "내용"], [
        ("테이블정보", "가상 쇼핑몰 도메인 테이블 11개, 컬럼 100여 개, 관계 13건"),
        ("쿼리정보", "4개 대분류 / 8개 소분류 아래 매출·정합성·재고 점검 쿼리 20건"),
        ("업무정보", "운영 절차 문서 8건 + 첨부파일 및 이미지"),
        ("공통코드", "주문상태·결제수단·회원등급 등 8개 코드 그룹"),
    ]) +
    "<h3>주의</h3><ul>"
    "<li>실제 운영 데이터, 실존 기업·기관·개인정보는 <b>포함되어 있지 않습니다</b>.</li>"
    "<li>SQL 은 오라클 문법 기준으로 작성되었으나 실행 검증은 되어 있지 않습니다.</li>"
    "<li>샘플을 다시 만들려면 <code>python sample_data/build_sample.py</code> 를 실행하세요.</li>"
    "</ul>")

DOC_CANCEL = h(
    "주문 취소·환불 처리 절차",
    "출고 여부에 따라 처리 경로가 갈린다. 잘못 태우면 재고와 정산이 동시에 틀어지므로 순서를 지킬 것.",
    "<h3>처리 경로</h3>" +
    tbl(["시점", "구분", "처리", "관련 테이블"], [
        ("출고 전", "취소(01)", "즉시 취소 후 PG 전체 취소", "TB_ORDER, TB_PAYMENT"),
        ("출고 후", "반품(02)", "회수 완료 확인 후 환불", "TB_CLAIM, TB_DELIVERY"),
        ("부분", "반품(02)", "해당 ITEM_SEQ 만 부분 취소", "TB_ORDER_ITEM, TB_PAYMENT"),
    ]) +
    "<h3>체크리스트</h3><ol>"
    "<li>TB_DELIVERY 의 INVOICE_NO 유무로 출고 여부를 먼저 확인한다.</li>"
    "<li>포인트 사용 주문은 POINT_USE_AMT 를 TB_POINT_HIST 에 원복 이력으로 남긴다.</li>"
    "<li>PG 취소 실패 시 CLAIM_STAT 을 보류로 두고 재시도 배치(매시 정각)에 맡긴다.</li>"
    "<li>부분 취소는 TB_ORDER.PAY_AMT 를 직접 수정하지 말고 결제 원장 기준으로 재계산한다.</li>"
    "</ol>"
    '<p style="color:#c84e34;"><b>주의</b> — 출고 후 건을 취소(01)로 처리하면 '
    '재고가 자동 복구되지 않아 실물과 어긋난다.</p>')

DOC_SETTLE = h(
    "월 정산 마감 절차",
    "매월 1일 오전에 전월 정산을 마감한다. 불일치 0건 확인이 선행 조건이다.",
    "<h3>일정</h3>" +
    tbl(["일자", "작업", "담당"], [
        ("매월 1일 09:00", "PG 원장 수신 및 대사 추출", "운영"),
        ("매월 1일 11:00", "불일치 검증 (0건 필수)", "운영/개발"),
        ("매월 1일 14:00", "수수료 계산 및 정산서 생성", "정산 배치"),
        ("매월 2일 10:00", "재무팀 승인 및 공급사 전송", "재무"),
    ]) +
    "<h3>선행 조건</h3><ul>"
    "<li>쿼리정보 > 이상 주문 점검 > <b>주문금액과 결제금액 불일치 건</b> 결과가 0건</li>"
    "<li>전월 접수 클레임 중 CLAIM_STAT 미완료 건 없음</li>"
    "<li>가상계좌 미입금 주문은 자동 취소 배치가 선행 완료되어야 함</li>"
    "</ul>"
    "<p>불일치가 발견되면 정산을 중단하고 PG 거래번호(PG_TID) 기준으로 개별 대사한다.</p>")

DOC_IDLE = h(
    "휴면회원 전환 및 복구 처리",
    "1년 이상 미접속 회원을 휴면(20)으로 전환한다. 전환 30일 전 사전 안내가 필수다.",
    "<h3>배치 정보</h3>" +
    tbl(["항목", "값"], [
        ("실행 주기", "매일 03:00"),
        ("대상", "MEMBER_STAT = '10' AND LAST_LOGIN_DT < ADD_MONTHS(SYSDATE, -12)"),
        ("사전 안내", "전환 30일 전 이메일 발송 (별도 배치 02:30)"),
        ("복구", "본인 인증 후 즉시 정상(10) 전환"),
    ]) +
    "<h3>유의사항</h3><ul>"
    "<li>휴면 전환 시 개인정보는 분리 보관 테이블로 이관된다. 원본 삭제가 아니다.</li>"
    "<li>미사용 포인트는 휴면 상태에서도 소멸되지 않으나 유효기간은 계속 진행된다.</li>"
    "<li>배치 실패 시 첨부된 SQL 로 수동 실행이 가능하다. 실행 전 대상 건수를 반드시 SELECT 로 확인할 것.</li>"
    "</ul>")

DOC_WITHDRAW = h(
    "회원 탈퇴 요청 처리",
    "탈퇴는 즉시 삭제가 아니라 상태 변경 후 보관 기간을 거친다.",
    tbl(["단계", "처리", "기간"], [
        ("1", "MEMBER_STAT 을 탈퇴(90)로 변경, WITHDRAW_DT 기록", "즉시"),
        ("2", "로그인·구매 차단, 마케팅 수신 대상 제외", "즉시"),
        ("3", "거래 기록 보관 (전자상거래법)", "5년"),
        ("4", "보관 기간 경과 후 파기 배치", "자동"),
    ]) +
    "<h3>선행 확인</h3><ul>"
    "<li>진행 중인 주문(ORDER_STAT 이 50, 90 이 아닌 건)이 있으면 탈퇴를 보류한다.</li>"
    "<li>미처리 클레임이 있으면 완료 후 처리한다.</li>"
    "<li>잔여 포인트는 탈퇴와 동시에 소멸되며 복구되지 않는다. 안내 필수.</li>"
    "</ul>")

DOC_DEPLOY = h(
    "정기 배포 체크리스트",
    "매주 목요일 20:00 정기 배포. 배치를 먼저 내리고 올리는 순서를 지킨다.",
    "<h3>순서</h3><ol>"
    "<li>DB 스키마 변경 스크립트 DBA 리뷰 완료 확인</li>"
    "<li>배치 스케줄 해제 (해제 확인까지)</li>"
    "<li>WAS 2대 순차 배포 — 1대 배포 후 헬스체크 통과 시 다음 진행</li>"
    "<li>공통코드 캐시 초기화</li>"
    "<li>스모크 테스트: 주문 생성 → 결제 승인 → 배송 등록</li>"
    "<li>배치 스케줄 재등록 및 다음 실행 시각 확인</li>"
    "</ol>"
    '<p style="color:#c84e34;"><b>롤백 기준</b> — 스모크 테스트 실패, 또는 배포 후 '
    '10분간 주문 생성 오류율 1% 초과 시 즉시 이전 빌드로 복귀한다.</p>')

DOC_INCIDENT = h(
    "장애 1차 조치 가이드 - 결제 승인 지연",
    "PG 응답 지연이 가장 흔한 장애 유형이다. 5분 안에 판단해서 에스컬레이션한다.",
    "<h3>증상</h3><ul>"
    "<li>PAY_STAT 이 승인대기(10)인 건이 누적</li>"
    "<li>애플리케이션 로그에 Read timed out 반복</li>"
    "</ul>"
    "<h3>1차 조치</h3><ol>"
    "<li>PG 사 상태 페이지 확인</li>"
    "<li>승인대기 건수 추이 확인 (5분 간격 2회)</li>"
    "<li>회복되지 않으면 대체 결제수단 안내 배너 노출 요청</li>"
    "</ol>" +
    tbl(["조건", "조치"], [
        ("승인대기 100건 초과", "결제팀 리드 호출"),
        ("10분 경과 회복 없음", "장애 상황 전파 및 공지 게시"),
        ("PG 사 장애 확인", "재시도 배치 중단 후 복구 시점 협의"),
    ]) +
    '<p style="color:#c84e34;"><b>금지</b> — 승인대기 건을 임의로 승인완료(20)로 '
    '변경하지 말 것. 미수금이 발생한다.</p>')

DOC_ONBOARD = h(
    "신규 입사자 개발 환경 세팅",
    "입사 첫 주에 완료해야 하는 항목이다. 계정 신청은 리드를 통해 진행한다.",
    tbl(["구분", "항목", "비고"], [
        ("계정", "사내 SSO, 형상관리, 이슈 트래커", "리드 승인 필요"),
        ("계정", "개발 DB 조회 계정", "DBA 신청, 운영은 불가"),
        ("도구", "JDK 17, IDE, DB 클라이언트", "사내 배포판 사용"),
        ("도구", "DB 돋보기", "테이블 명세 조회용"),
        ("문서", "도메인 용어집, 코드 컨벤션", "위키 참조"),
    ]) +
    "<h3>첫 주 과제</h3><ul>"
    "<li>주문 → 결제 → 배송 흐름을 테이블 관계도로 직접 그려본다.</li>"
    "<li>쿼리정보의 '일자별 주문/매출 집계'를 개발 DB에서 실행해 본다.</li>"
    "<li>공통코드 8개 그룹의 의미를 파악한다.</li>"
    "</ul>"
    '<p style="color:#c84e34;">운영 DB 직접 접속은 금지되어 있다. 조회가 필요하면 DBA에게 요청한다.</p>')

DOC_GLOSSARY = h(
    "도메인 용어집",
    "회의나 이슈에서 자주 쓰이는 용어를 정리한다.",
    tbl(["용어", "설명", "관련 테이블"], [
        ("클레임", "취소·반품·교환을 아우르는 상위 개념", "TB_CLAIM"),
        ("대사", "PG 원장과 자사 결제 원장을 대조하는 작업", "TB_PAYMENT"),
        ("고아 데이터", "부모 행 없이 남은 자식 행", "TB_ORDER_ITEM"),
        ("휴면", "1년 이상 미접속으로 분리 보관된 회원 상태", "TB_MEMBER"),
        ("스모크 테스트", "배포 직후 핵심 흐름만 빠르게 확인하는 검증", "-"),
        ("미수금", "승인되지 않았는데 완료 처리되어 회수 못 한 금액", "TB_PAYMENT"),
    ]))


# ---------------------------------------------------------------- 첨부 텍스트
FILE_CANCEL_PROC = """[샘플] 주문 취소·환불 처리 절차서 v1.2
====================================================
※ 본 문서는 데모용 샘플입니다. 실제 업무 문서가 아닙니다.

1. 적용 범위
   - 온라인 주문 채널을 통해 접수된 모든 취소/반품/교환 건

2. 처리 원칙
   2.1 출고 전 요청은 취소(CLAIM_TYPE=01)로 처리한다.
   2.2 출고 후 요청은 반품(CLAIM_TYPE=02)으로 전환한다.
   2.3 교환(03)은 회수와 재발송을 하나의 클레임으로 관리한다.

3. 환불 기준
   3.1 카드 결제  : PG 승인 취소 (영업일 3~5일 소요)
   3.2 계좌이체   : 환불 계좌 확인 후 익영업일 지급
   3.3 가상계좌   : 입금 확인된 건만 환불 대상
   3.4 포인트     : 즉시 원복, 단 유효기간은 원 적립일 기준 유지

4. 부분 취소
   4.1 ITEM_SEQ 단위로 처리한다.
   4.2 배송비는 잔여 주문금액이 무료배송 기준 미만이 되면 재부과한다.

5. 예외 처리
   5.1 PG 취소 실패 → CLAIM_STAT 보류, 재시도 배치(매시 정각)
   5.2 회수 미도착 14일 경과 → 고객 안내 후 클레임 철회 검토

6. 개정 이력
   v1.0  최초 작성
   v1.1  부분 취소 시 배송비 재부과 기준 추가
   v1.2  가상계좌 미입금 건 처리 기준 명확화
"""

FILE_SETTLE_CSV = """구분,점검항목,기준,담당,비고
1,PG 원장 수신,전월 전체 거래 수신 완료,운영,매월 1일 09:00
2,주문-결제 금액 불일치,0건,운영,불일치 시 마감 중단
3,미처리 클레임,0건,CS,이월 시 재무 협의
4,가상계좌 미입금 자동취소,배치 완료,운영,선행 조건
5,결제수단별 수수료율,계약서 대조,재무,연 1회 갱신
6,공급사별 정산서 생성,공급사 수와 일치,정산배치,
7,정산서 합계 검증,원장 합계와 일치,재무,
8,재무팀 승인,승인 완료,재무,매월 2일 10:00
"""

FILE_IDLE_SQL = """-- [샘플] 휴면회원 전환 수동 실행 스크립트
-- ※ 데모용 샘플입니다. 실제 운영 스크립트가 아닙니다.
-- 배치(매일 03:00) 실패 시에만 사용한다.

-- 1) 대상 건수 확인 (반드시 먼저 실행)
SELECT COUNT(*) AS TARGET_CNT
  FROM TB_MEMBER
 WHERE MEMBER_STAT   = '10'
   AND LAST_LOGIN_DT < ADD_MONTHS(SYSDATE, -12);

-- 2) 대상 목록 백업
CREATE TABLE TMP_IDLE_BACKUP_20260720 AS
SELECT MEMBER_ID, MEMBER_STAT, LAST_LOGIN_DT, SYSDATE AS BACKUP_DT
  FROM TB_MEMBER
 WHERE MEMBER_STAT   = '10'
   AND LAST_LOGIN_DT < ADD_MONTHS(SYSDATE, -12);

-- 3) 전환
UPDATE TB_MEMBER
   SET MEMBER_STAT = '20'
     , UPD_DT      = SYSDATE
 WHERE MEMBER_STAT   = '10'
   AND LAST_LOGIN_DT < ADD_MONTHS(SYSDATE, -12);

-- 4) 반영 건수가 1) 과 일치하는지 확인 후
-- COMMIT;
-- 불일치 시
-- ROLLBACK;
"""

FILE_ROLLBACK = """[샘플] 배포 롤백 절차
====================================================
※ 데모용 샘플입니다.

판단 기준
  - 스모크 테스트 실패
  - 배포 후 10분간 주문 생성 오류율 1% 초과
  - DB 스키마 변경으로 인한 애플리케이션 기동 실패

롤백 순서
  1. 배치 스케줄 재해제
  2. WAS 2대를 이전 빌드로 순차 복귀
  3. 공통코드 캐시 초기화
  4. 스키마 변경이 있었다면 DBA 입회하에 down 스크립트 실행
     ※ 데이터 손실 가능성이 있으면 롤백보다 hotfix 를 우선 검토
  5. 스모크 테스트 재수행
  6. 배치 스케줄 재등록

복귀 후
  - 장애 보고서 작성 (24시간 내)
  - 원인 분석 및 재발 방지 항목 도출
"""


# ---------------------------------------------------------------- 업무정보 트리
# doc: (제목, 본문, 즐겨찾기, 반복설정, [(파일명, 내용)], [(이미지명, 생성함수)])
# 반복설정: None 또는 (recurrence_type, recurrence_value, start_date, end_date)
#   daily_interval  : "N"        - N일마다
#   weekly_interval : "N|d,d"    - N주마다 / 요일(ISO: 월=1 ~ 일=7)
#   monthly_day     : "N"|"last" - 매월 N일 / 말일
TASK_TREE = [
    ("안내", [
        ("[필독] 이 데이터는 샘플입니다", DOC_INTRO, 1, None, [], []),
    ]),
    ("주문/결제 운영", [
        ("주문 취소·환불 처리 절차", DOC_CANCEL, 1, None,
         [("주문취소_처리절차_v1.2.txt", FILE_CANCEL_PROC)],
         [("주문취소_처리흐름.png", img_order_cancel_flow),
          ("주문도메인_ERD.png", img_erd_order)]),
        ("월 정산 마감 절차", DOC_SETTLE, 1, ("monthly_day", "1", "2026-01-01", None),
         [("정산마감_체크리스트.csv", FILE_SETTLE_CSV)],
         [("정산마감_프로세스.png", img_settlement_process)]),
    ]),
    ("회원 운영", [
        ("휴면회원 전환 및 복구 처리", DOC_IDLE, 0, ("daily_interval", "1", "2026-01-01", None),
         [("휴면회원_전환_배치.sql", FILE_IDLE_SQL)], []),
        ("회원 탈퇴 요청 처리", DOC_WITHDRAW, 0, None, [], []),
    ]),
    ("배포/장애 대응", [
        ("정기 배포 체크리스트", DOC_DEPLOY, 1, ("weekly_interval", "1|4", "2026-03-01", None),
         [("배포_롤백_절차.txt", FILE_ROLLBACK)],
         [("배포_체크보드.png", img_deploy_board)]),
        ("장애 1차 조치 - 결제 승인 지연", DOC_INCIDENT, 0, None, [],
         [("장애화면_결제승인지연.png", img_error_screen)]),
    ]),
    ("온보딩", [
        ("신규 입사자 개발 환경 세팅", DOC_ONBOARD, 0, None, [],
         [("개발환경_구성도.png", img_dev_env)]),
        ("도메인 용어집", DOC_GLOSSARY, 0, None, [], []),
    ]),
]


# ---------------------------------------------------------------- 빌드
def build():
    # 1. 기존 산출물 제거 (샘플은 항상 처음부터 다시 만든다)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"removed  : {DB_PATH}")
    if os.path.isdir(ATTACH_DIR):
        shutil.rmtree(ATTACH_DIR)
        print(f"removed  : {ATTACH_DIR}")
    os.makedirs(ATTACH_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    # 2. 테이블 / 컬럼 / 관계
    for name, ko, cat, fav in TABLES:
        cur.execute(
            "INSERT INTO tables (table_name, table_ko_name, task_category, is_favorite, updated_at)"
            " VALUES (?, ?, ?, ?, ?)", (name, ko, cat, fav, NOW_S))

    order_by_cat = {}
    for name, ko, cat, _ in TABLES:
        order_by_cat[cat] = order_by_cat.get(cat, 0) + 1
        cur.execute(
            "INSERT INTO table_categories (table_name, task_category, task_order, display_name)"
            " VALUES (?, ?, ?, ?)", (name, cat, order_by_cat[cat], ko))

    col_cnt = 0
    for tname, cols in COLUMNS.items():
        for (cname, cko, dtype, length, nullable, pk, sel, whr) in cols:
            cur.execute(
                "INSERT INTO columns (table_name, column_name, column_ko_name, data_type,"
                " length, is_nullable, is_pk, is_selected, is_where)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (tname, cname, cko, dtype, length, nullable, pk, sel, whr))
            col_cnt += 1

    for src_t, src_c, ref_t in RELATIONS:
        cur.execute(
            "INSERT INTO relations (src_table_name, src_column_name, ref_table_name)"
            " VALUES (?, ?, ?)", (src_t, src_c, ref_t))

    # 3. 공통코드
    code_cnt = 0
    for grp_id, col_name, grp_name, items in CODE_GROUPS:
        cur.execute("INSERT INTO COMMON_CODE_MASTER VALUES (?, ?, ?, ?, ?)",
                    (grp_id, col_name, grp_name, "Y", SAMPLE_OWNER))
        for i, (val, nm, desc) in enumerate(items, start=1):
            cur.execute("INSERT INTO COMMON_CODE_SUB VALUES (?, ?, ?, ?, ?, ?)",
                        (grp_id, val, nm, desc, "Y", i))
            cur.execute(
                "INSERT INTO common_codes (column_name, code_group_id, code_group_name,"
                " code_value, code_ko_name, description) VALUES (?, ?, ?, ?, ?, ?)",
                (col_name, grp_id, grp_name, val, nm, desc))
            code_cnt += 1

    # 4. 쿼리
    q_cnt = 0
    for top_i, (top_name, subs) in enumerate(QUERY_TREE, start=1):
        cur.execute(
            "INSERT INTO query_categories (category_name, parent_id, sort_order, created_at)"
            " VALUES (?, NULL, ?, ?)", (top_name, top_i, ts(30)))
        top_id = cur.lastrowid
        for sub_i, (sub_name, queries) in enumerate(subs, start=1):
            cur.execute(
                "INSERT INTO query_categories (category_name, parent_id, sort_order, created_at)"
                " VALUES (?, ?, ?, ?)", (sub_name, top_id, sub_i, ts(30)))
            sub_id = cur.lastrowid
            for q_i, (title, sql, desc, fav) in enumerate(queries, start=1):
                cur.execute(
                    "INSERT INTO queries (category_id, query_title, query_content,"
                    " description, created_at, is_favorite, sort_order)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (sub_id, title, sql, desc, ts(25 - q_i), fav, q_i))
                q_cnt += 1

    for title, content, when in RECENT_QUERIES:
        cur.execute(
            "INSERT INTO recent_queries (query_title, query_content, copied_at)"
            " VALUES (?, ?, ?)", (title, content, when))
    for tname, when in RECENT_TABLES:
        cur.execute("INSERT INTO recent_tables (table_name, viewed_at) VALUES (?, ?)",
                    (tname, when))

    # 5. 업무정보 + 첨부
    doc_cnt = att_cnt = 0
    for cat_i, (cat_name, docs) in enumerate(TASK_TREE, start=1):
        cur.execute(
            "INSERT INTO task_doc_categories (category_name, parent_id, sort_order, created_at)"
            " VALUES (?, NULL, ?, ?)", (cat_name, cat_i, ts(40)))
        cat_id = cur.lastrowid
        for d_i, (title, content, fav, repeat, files, images) in enumerate(docs, start=1):
            if repeat:
                r_type, r_val, s_dt, e_dt = repeat
                is_rep, has_period = 1, 1
            else:
                r_type = r_val = s_dt = e_dt = None
                is_rep = has_period = 0
            cur.execute(
                "INSERT INTO task_documents (category_id, title, content, created_at,"
                " updated_at, is_favorite, sort_order, is_repeating, recurrence_type,"
                " recurrence_value, has_period, start_date, end_date)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cat_id, title, content, ts(40 - d_i), ts(d_i), fav, d_i,
                 is_rep, r_type, r_val, has_period, s_dt, e_dt))
            doc_id = cur.lastrowid
            doc_cnt += 1

            if not files and not images:
                continue
            doc_dir = os.path.join(ATTACH_DIR, f"task_{doc_id}")
            os.makedirs(doc_dir, exist_ok=True)

            for fname, body in files:
                fpath = os.path.join(doc_dir, fname)
                with open(fpath, "w", encoding="utf-8") as fp:
                    fp.write(body)
                cur.execute(
                    "INSERT INTO task_doc_attachments (doc_id, file_path, file_name,"
                    " file_size, created_at, is_embed) VALUES (?, ?, ?, ?, ?, 0)",
                    (doc_id, f"attachments/task_{doc_id}/{fname}", fname,
                     os.path.getsize(fpath), ts(5)))
                att_cnt += 1

            for iname, gen in images:
                ipath = os.path.join(doc_dir, iname)
                gen(ipath)
                cur.execute(
                    "INSERT INTO task_doc_attachments (doc_id, file_path, file_name,"
                    " file_size, created_at, is_embed) VALUES (?, ?, ?, ?, ?, 1)",
                    (doc_id, f"attachments/task_{doc_id}/{iname}", iname,
                     os.path.getsize(ipath), ts(5)))
                att_cnt += 1

    # 6. 앱 메타데이터 (샘플 표식)
    meta = [
        ("is_sample_data", "Y"),
        ("sample_notice", SAMPLE_TAG),
        ("sample_domain", "가상 온라인 쇼핑몰 (SHOPDB)"),
        ("sample_built_at", NOW_S),
        ("sample_builder", "sample_data/build_sample.py"),
        ("schema_owner", SAMPLE_OWNER),
    ]
    cur.executemany("INSERT INTO app_metadata (key, value) VALUES (?, ?)", meta)

    conn.commit()
    cur.execute("VACUUM")
    conn.close()

    print("-" * 52)
    print(f"테이블   : {len(TABLES)}건")
    print(f"컬럼     : {col_cnt}건")
    print(f"관계     : {len(RELATIONS)}건")
    print(f"공통코드 : {len(CODE_GROUPS)}그룹 / {code_cnt}건")
    print(f"쿼리     : {q_cnt}건")
    print(f"업무문서 : {doc_cnt}건, 첨부 {att_cnt}건")
    print(f"DB 크기  : {os.path.getsize(DB_PATH) / 1024:.0f} KB")
    print("-" * 52)
    print("완료:", DB_PATH)


if __name__ == "__main__":
    build()
