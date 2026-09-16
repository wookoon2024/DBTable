# -*- coding: utf-8 -*-
"""
DB 돋보기 - 테이블 관계도(ERD) 표준 그래픽 위젯 모듈
=====================================================
- 국제 표준 IE(Information Engineering / Crow's Foot) 표기법 준수
- 직각 배선(Orthogonal / Manhattan Routing) 및 모서리 라운딩
- 엔티티 박스: PK 영역(골드 배지) / 일반 속성 영역(블루 FK 배지) 분리
- 계층형(Hierarchical / Sugiyama-style) 자동 배치 및 충돌 방지
- 인터랙티브 선택 하이라이트, 테이블 드래그 이동, 확대/축소/미니맵 지원
"""
import json
import math
from collections import defaultdict

from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import (
    QFont, QFontMetrics, QColor, QCursor, QPainter, QPen, QBrush,
    QPainterPath, QImage
)
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem


class ErdTableBox:
    """ERD 다이어그램에 배치되는 표준 엔티티(테이블) 박스 레이아웃 정보"""

    def __init__(self, table_name, table_ko_name, columns, fk_set=None):
        self.table_name = table_name
        self.table_ko_name = table_ko_name or ""
        self.columns = columns or []
        self.fk_set = fk_set or set()
        self.x = 0.0
        self.y = 0.0
        self.is_selected = False
        self.is_neighbor = False
        self.show_compact = False
        self.show_ko_columns = True

        self.pk_cols = [c for c in self.columns if str(c.get("is_pk") or "").upper() in ("Y", "1", "TRUE")]
        self.normal_cols = [c for c in self.columns if str(c.get("is_pk") or "").upper() not in ("Y", "1", "TRUE")]

        self.header_h = 36.0
        self.row_h = 23.0
        self.divider_h = 6.0
        self.footer_h = 6.0
        self.width = 310.0
        self._recalculate_size()

    def _recalculate_size(self):
        cols_to_show = self.visible_columns
        self.height = self.header_h + (len(cols_to_show) * self.row_h) + self.footer_h
        if self.pk_cols and self.normal_cols and not self.show_compact:
            self.height += self.divider_h

    @property
    def visible_columns(self):
        if self.show_compact:
            return [c for c in self.columns if self.is_pk(c) or c.get("column_name") in self.fk_set]
        return self.columns

    @staticmethod
    def is_pk(col):
        return str(col.get("is_pk") or "").upper() in ("Y", "1", "TRUE")

    def is_fk(self, col):
        return col.get("column_name") in self.fk_set

    def rect(self):
        return QRectF(self.x, self.y, self.width, self.height)

    def contains(self, pt):
        return self.rect().contains(pt)

    def get_column_y(self, col_name):
        """지정된 컬럼 행의 중앙 Y 좌표를 반환"""
        cols = self.visible_columns
        curr_y = self.y + self.header_h
        has_divider = bool(self.pk_cols and self.normal_cols and not self.show_compact)
        pk_count = len([c for c in cols if self.is_pk(c)])

        for idx, c in enumerate(cols):
            if idx == pk_count and has_divider:
                curr_y += self.divider_h
            if c.get("column_name") == col_name:
                return curr_y + self.row_h / 2.0
            curr_y += self.row_h

        # 매칭되는 컬럼이 없으면 첫 번째 PK 또는 헤더 중앙
        if self.pk_cols:
            return self.y + self.header_h + self.row_h / 2.0
        return self.y + self.header_h / 2.0

    def left_anchor(self, col_name=None):
        return QPointF(self.x, self.get_column_y(col_name))

    def right_anchor(self, col_name=None):
        return QPointF(self.x + self.width, self.get_column_y(col_name))

    def first_pk_index(self):
        return 0


class ErdCanvasItem(QGraphicsItem):
    """표준 ERD 전체(엔티티 박스 + 직각 배선 관계선)를 렌더링하는 그래픽 아이템"""

    def __init__(self, boxes, relations, show_self_ref=True):
        super().__init__()
        self.boxes = {b.table_name: b for b in boxes}
        self.relations = relations or []
        self.show_self_ref = show_self_ref
        self.selected_table = None
        self.show_compact = False
        self.show_ko_columns = True
        self._item_rect = QRectF(0, 0, 100, 100)

    def set_selected_table(self, table_name):
        """테이블 선택 시 해당 테이블 및 인접 테이블/관계선 강조"""
        self.selected_table = table_name
        neighbors = set()
        if table_name:
            for rel in self.relations:
                src = rel.get("src_table_name")
                ref = rel.get("ref_table_name")
                if src == table_name and ref in self.boxes:
                    neighbors.add(ref)
                elif ref == table_name and src in self.boxes:
                    neighbors.add(src)

        for b in self.boxes.values():
            b.is_selected = (b.table_name == table_name)
            b.is_neighbor = (b.table_name in neighbors)

    def set_show_compact(self, compact):
        self.show_compact = compact
        for b in self.boxes.values():
            b.show_compact = compact
            b._recalculate_size()

    def set_show_ko_columns(self, show_ko):
        self.show_ko_columns = show_ko
        for b in self.boxes.values():
            b.show_ko_columns = show_ko

    # ---------- 계층형 스마트 자동 배치 ----------
    def auto_layout(self):
        """국제 표준 좌-우 계층형(Hierarchical Sugiyama-style) 자동 배치 알고리즘
        
        - 공통 감사 컬럼(REG_ID 등)을 제외한 순수 비즈니스 외래키 관계를 분석하여 계층(Tier) 결정
        - Level 0: 마스터/기준 테이블 (TB_MEMBER, TB_CATEGORY, TB_ROLE, TB_MENU 등)
        - Level 1: 주요 업무 엔티티 (TB_PRODUCT, TB_ORDER 등)
        - Level 2~3: 상세/이력 엔티티 (TB_ORDER_ITEM, TB_PAYMENT, TB_DELIVERY 등)
        - 열(Column)당 최대 개수를 제한하여 완만한 직사각형 비율(Aspect Ratio) 유지
        - Barycenter(중심점) 정렬을 통해 선 교차 최소화
        """
        if not self.boxes:
            return

        names = list(self.boxes.keys())

        # 감사 컬럼을 제외한 순수 비즈니스 관계 그래프 빌드
        parents = defaultdict(set)
        children = defaultdict(set)
        all_parents = defaultdict(set)

        for rel in self.relations:
            src = rel.get("src_table_name")
            ref = rel.get("ref_table_name")
            col = rel.get("src_column_name") or ""
            if src in self.boxes and ref in self.boxes and src != ref:
                all_parents[src].add(ref)
                if col.upper() not in ("REG_ID", "UPD_ID", "MOD_ID", "CREATE_ID"):
                    parents[src].add(ref)
                    children[ref].add(src)

        # 1. 루트 엔티티(외래키 없는 기준 테이블) Level 0 지정
        levels = {}
        for name in names:
            if len(parents[name]) == 0:
                levels[name] = 0

        # 2. 위상 정렬 기반 레벨 전파
        for _ in range(6):
            for src, p_set in parents.items():
                if p_set:
                    max_p_lvl = max(levels.get(p, 0) for p in p_set)
                    levels[src] = max(levels.get(src, 0), max_p_lvl + 1)

        for name in names:
            if name not in levels:
                levels[name] = 0

        # 3. 레벨별 그룹화 및 열 균형 조정 (한 열에 6개 이상이면 분할)
        max_lvl = max(levels.values()) if levels else 0
        level_groups = defaultdict(list)
        for name in names:
            level_groups[levels[name]].append(name)

        new_level_groups = defaultdict(list)
        curr_col = 0
        for lvl in range(max_lvl + 1):
            items = level_groups[lvl]
            if len(items) > 6:
                chunks = [items[i:i + 5] for i in range(0, len(items), 5)]
                for chunk in chunks:
                    new_level_groups[curr_col] = chunk
                    curr_col += 1
            else:
                new_level_groups[curr_col] = items
                curr_col += 1

        level_groups = new_level_groups
        total_cols = curr_col

        # 4. Barycenter 정렬 (부모 테이블 Y 좌표 평균을 기준으로 정렬하여 교차선 최소화)
        for col_idx in range(1, total_cols):
            group = level_groups[col_idx]
            def get_bc(nm):
                p_nodes = all_parents[nm]
                placed = [self.boxes[p].y for p in p_nodes if p in self.boxes and self.boxes[p].x < (col_idx * 400)]
                return (sum(placed) / len(placed)) if placed else 9999.0
            group.sort(key=get_bc)

        # 5. 최종 좌표 할당 (여백 확보로 테이블 겹침 완전 방지)
        col_x_start = 60.0
        col_gap = 120.0
        row_gap = 35.0

        current_x = col_x_start
        for col_idx in range(total_cols):
            group = level_groups[col_idx]
            if not group:
                continue

            current_y = 60.0
            max_w = 0.0
            for name in group:
                box = self.boxes[name]
                box.x = current_x
                box.y = current_y
                current_y += box.height + row_gap
                max_w = max(max_w, box.width)

            current_x += max_w + col_gap

    def boundingRect(self):
        if not self.boxes:
            return self._item_rect
        min_x = min(b.x for b in self.boxes.values())
        min_y = min(b.y for b in self.boxes.values())
        max_x = max(b.x + b.width for b in self.boxes.values())
        max_y = max(b.y + b.height for b in self.boxes.values())
        self._item_rect = QRectF(
            min_x - 60.0, min_y - 60.0,
            (max_x - min_x) + 120.0, (max_y - min_y) + 120.0
        )
        return self._item_rect

    # ---------- 그리기 ----------
    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # 1. 배경 도트 격자
        self._paint_background(painter)

        # 2. 직각 배선 관계선 (Crow's foot 기호 포함)
        for rel in self.relations:
            self._paint_relation(painter, rel)

        # 3. 표준 엔티티 박스 (PK/FK 영역 및 배지)
        for box in self.boxes.values():
            self._paint_box(painter, box)

    def _paint_background(self, painter):
        rect = self.boundingRect()
        painter.fillRect(rect, QColor("#F8FAFC"))

        # 엔지니어링 도트 그리드
        dot_pen = QPen(QColor("#CBD5E1"))
        dot_pen.setWidth(2)
        painter.setPen(dot_pen)

        start_x = int(rect.x() / 24) * 24
        end_x = int((rect.x() + rect.width()) / 24 + 1) * 24
        start_y = int(rect.y() / 24) * 24
        end_y = int((rect.y() + rect.height()) / 24 + 1) * 24

        for x in range(start_x, end_x, 24):
            for y in range(start_y, end_y, 24):
                painter.drawPoint(x, y)

    def _paint_box(self, painter, box):
        r = box.rect()

        # 부드러운 드롭 섀도우
        shadow_rect = r.translated(3, 4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 16)))
        painter.drawRoundedRect(shadow_rect, 7.0, 7.0)

        # 몸체 배경
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        if box.is_selected:
            painter.setPen(QPen(QColor("#2563EB"), 2.4))
        elif box.is_neighbor:
            painter.setPen(QPen(QColor("#3B82F6"), 1.8))
        else:
            painter.setPen(QPen(QColor("#CBD5E1"), 1.2))

        painter.drawRoundedRect(r, 6.0, 6.0)

        # 상단 헤더 (라운드 클리핑)
        path = QPainterPath()
        path.moveTo(r.x(), r.y() + 6.0)
        path.quadTo(r.x(), r.y(), r.x() + 6.0, r.y())
        path.lineTo(r.x() + r.width() - 6.0, r.y())
        path.quadTo(r.x() + r.width(), r.y(), r.x() + r.width(), r.y() + 6.0)
        path.lineTo(r.x() + r.width(), r.y() + box.header_h)
        path.lineTo(r.x(), r.y() + box.header_h)
        path.closeSubpath()

        header_color = QColor("#1E3A8A") if not box.is_selected else QColor("#1D4ED8")
        painter.fillPath(path, QBrush(header_color))

        # 헤더 타이틀 (영문 물리명 볼드 + 한글 논리명)
        painter.setPen(QColor("#FFFFFF"))
        font_header_en = QFont("Segoe UI", 10, QFont.Weight.Bold)
        font_header_ko = QFont("Malgun Gothic", 9, QFont.Weight.Normal)

        painter.setFont(font_header_en)
        en_text = box.table_name
        ko_text = f" [{box.table_ko_name}]" if box.table_ko_name else ""

        text_x = r.x() + 10.0
        text_y = r.y() + box.header_h / 2.0 + 4.0

        painter.drawText(int(text_x), int(text_y), en_text)
        en_w = QFontMetrics(font_header_en).horizontalAdvance(en_text)

        if ko_text:
            painter.setFont(font_header_ko)
            painter.setPen(QColor("#93C5FD"))
            painter.drawText(int(text_x + en_w), int(text_y), ko_text)

        # 컬럼 속성 행 렌더링
        curr_y = r.y() + box.header_h
        cols_to_show = box.visible_columns
        has_divider = bool(box.pk_cols and box.normal_cols and not box.show_compact)
        pk_count = len([c for c in cols_to_show if box.is_pk(c)])

        font_name = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
        font_ko_col = QFont("Malgun Gothic", 8, QFont.Weight.Normal)
        font_type = QFont("Segoe UI", 8, QFont.Weight.Normal)
        font_badge = QFont("Segoe UI", 7, QFont.Weight.Bold)

        for idx, col in enumerate(cols_to_show):
            # PK 섹션과 일반 속성 섹션을 가르는 굵은 구분선
            if idx == pk_count and has_divider:
                div_rect = QRectF(r.x(), curr_y, r.width(), box.divider_h)
                painter.fillRect(div_rect, QColor("#F1F5F9"))
                painter.setPen(QPen(QColor("#CBD5E1"), 1.2))
                painter.drawLine(int(r.x()), int(curr_y + 3), int(r.x() + r.width()), int(curr_y + 3))
                curr_y += box.divider_h

            row_rect = QRectF(r.x() + 1.0, curr_y, r.width() - 2.0, box.row_h)
            is_pk = box.is_pk(col)
            is_fk = box.is_fk(col)

            # 행 배경색 (PK는 은은한 골드 틴트, 일반 컬럼은 스트라이프)
            if is_pk:
                painter.fillRect(row_rect, QColor("#FEF9C3"))
            elif idx % 2 == 1:
                painter.fillRect(row_rect, QColor("#F8FAFC"))
            else:
                painter.fillRect(row_rect, QColor("#FFFFFF"))

            # 키 배지 (PK: 골드, FK: 블루, PF: 보라)
            badge_x = r.x() + 8.0
            badge_y = curr_y + (box.row_h - 14.0) / 2.0
            badge_rect = QRectF(badge_x, badge_y, 22.0, 14.0)

            if is_pk and is_fk:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor("#7C3AED")))
                painter.drawRoundedRect(badge_rect, 3.0, 3.0)
                painter.setFont(font_badge)
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "PF")
            elif is_pk:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor("#D97706")))
                painter.drawRoundedRect(badge_rect, 3.0, 3.0)
                painter.setFont(font_badge)
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "PK")
            elif is_fk:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor("#2563EB")))
                painter.drawRoundedRect(badge_rect, 3.0, 3.0)
                painter.setFont(font_badge)
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "FK")

            # 컬럼 물리명
            col_name_x = r.x() + 35.0
            col_name_y = curr_y + box.row_h / 2.0 + 4.0
            col_name = col.get("column_name") or ""
            painter.setFont(font_name)
            painter.setPen(QColor("#0F172A"))
            painter.drawText(int(col_name_x), int(col_name_y), col_name)

            # 컬럼 논리명 (한글명)
            col_ko = col.get("column_ko_name") or ""
            name_w = QFontMetrics(font_name).horizontalAdvance(col_name)
            if col_ko and box.show_ko_columns:
                painter.setFont(font_ko_col)
                painter.setPen(QColor("#64748B"))
                avail_w = r.width() - (name_w + 35.0 + 95.0)
                if avail_w > 20:
                    elided = QFontMetrics(font_ko_col).elidedText(f"({col_ko})", Qt.TextElideMode.ElideRight, int(avail_w))
                    painter.drawText(int(col_name_x + name_w + 6.0), int(col_name_y), elided)

            # 데이터 타입 (우측 정렬)
            dtype = col.get("data_type") or ""
            length = col.get("length")
            if length and dtype in ("VARCHAR2", "CHAR", "NUMBER"):
                dtype = f"{dtype}({length})"

            painter.setFont(font_type)
            painter.setPen(QColor("#475569"))
            dtype_w = QFontMetrics(font_type).horizontalAdvance(dtype)
            dtype_x = r.x() + r.width() - dtype_w - 28.0
            painter.drawText(int(dtype_x), int(col_name_y), dtype)

            # Not Null 배지 (NN)
            is_nn = str(col.get("is_nullable") or "").upper() == "N"
            if is_nn:
                painter.setFont(font_badge)
                painter.setPen(QColor("#DC2626"))
                painter.drawText(int(r.x() + r.width() - 20.0), int(col_name_y - 1), "NN")

            curr_y += box.row_h

    def _paint_relation(self, painter, rel):
        src = self.boxes.get(rel.get("src_table_name"))
        ref = self.boxes.get(rel.get("ref_table_name"))
        if not src or not ref:
            return

        is_self = (src is ref)
        if is_self:
            if self.show_self_ref:
                self._paint_self_relation(painter, src, rel)
            return

        src_col_name = rel.get("src_column_name")
        ref_col_name = rel.get("ref_column_name")

        # 식별 관계 여부 판별 (외래키가 자식의 PK에 포함되는가)
        is_identifying = False
        for c in src.columns:
            if c.get("column_name") == src_col_name and src.is_pk(c):
                is_identifying = True
                break

        # 직각 배선 라우팅 (스마트 포트 선택)
        if src.x >= (ref.x + ref.width):
            p1 = src.left_anchor(src_col_name)
            p4 = ref.right_anchor(ref_col_name)
            mid_x = (p1.x() + p4.x()) / 2.0
            pts = [p1, QPointF(mid_x, p1.y()), QPointF(mid_x, p4.y()), p4]
            crow_dir = 1.0
            parent_dir = -1.0
        elif (src.x + src.width) <= ref.x:
            p1 = src.right_anchor(src_col_name)
            p4 = ref.left_anchor(ref_col_name)
            mid_x = (p1.x() + p4.x()) / 2.0
            pts = [p1, QPointF(mid_x, p1.y()), QPointF(mid_x, p4.y()), p4]
            crow_dir = -1.0
            parent_dir = 1.0
        else:
            side_x = max(src.x + src.width, ref.x + ref.width) + 30.0
            p1 = src.right_anchor(src_col_name)
            p4 = ref.right_anchor(ref_col_name)
            pts = [p1, QPointF(side_x, p1.y()), QPointF(side_x, p4.y()), p4]
            crow_dir = -1.0
            parent_dir = -1.0

        # 선택 하이라이트 스타일링
        is_highlighted = (self.selected_table in (src.table_name, ref.table_name))
        if is_highlighted:
            line_color = QColor("#2563EB")
            line_width = 2.2
        elif self.selected_table is not None:
            line_color = QColor("#E2E8F0")
            line_width = 1.2
        else:
            line_color = QColor("#64748B")
            line_width = 1.6

        # 식별 관계는 실선, 비식별 관계는 점선
        pen_style = Qt.PenStyle.SolidLine if is_identifying else Qt.PenStyle.DashLine
        pen = QPen(line_color, line_width, pen_style, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # 부드러운 코너 라운딩 적용 직각 경로
        path = QPainterPath()
        path.moveTo(pts[0])
        radius = 8.0

        for i in range(1, len(pts) - 1):
            p_prev = pts[i - 1]
            p_curr = pts[i]
            p_next = pts[i + 1]

            v1 = QPointF(p_curr.x() - p_prev.x(), p_curr.y() - p_prev.y())
            v2 = QPointF(p_next.x() - p_curr.x(), p_next.y() - p_curr.y())
            len1 = math.hypot(v1.x(), v1.y())
            len2 = math.hypot(v2.x(), v2.y())

            r = min(radius, len1 / 2.0, len2 / 2.0)
            if len1 > 0 and len2 > 0 and r > 0:
                p_before = QPointF(p_curr.x() - (v1.x() / len1) * r, p_curr.y() - (v1.y() / len1) * r)
                p_after = QPointF(p_curr.x() + (v2.x() / len2) * r, p_curr.y() + (v2.y() / len2) * r)
                path.lineTo(p_before)
                path.quadTo(p_curr, p_after)
            else:
                path.lineTo(p_curr)

        path.lineTo(pts[-1])
        painter.drawPath(path)

        # 말단 심볼(Crow's foot 및 평행 바)은 실선으로 선명하게 렌더링
        marker_pen = QPen(line_color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(marker_pen)

        self._draw_crows_foot(painter, pts[0], crow_dir)
        self._draw_parent_bar(painter, pts[-1], parent_dir)

    def _draw_crows_foot(self, painter, pt, direction):
        """자식(N) 측 까마귀발 삼지창 기호 및 필수 바"""
        foot_len = 12.0 * direction
        spread = 6.0

        neck = QPointF(pt.x() + foot_len, pt.y())
        p_mid = pt
        p_top = QPointF(pt.x(), pt.y() - spread)
        p_bot = QPointF(pt.x(), pt.y() + spread)

        painter.drawLine(neck, p_mid)
        painter.drawLine(neck, p_top)
        painter.drawLine(neck, p_bot)

        # 필수 선 (|)
        bar_x = pt.x() + (16.0 * direction)
        painter.drawLine(QPointF(bar_x, pt.y() - 6.0), QPointF(bar_x, pt.y() + 6.0))

    def _draw_parent_bar(self, painter, pt, direction):
        """부모(1) 측 평행 바(||) 기호"""
        b1_x = pt.x() + (8.0 * direction)
        b2_x = pt.x() + (14.0 * direction)
        painter.drawLine(QPointF(b1_x, pt.y() - 6.0), QPointF(b1_x, pt.y() + 6.0))
        painter.drawLine(QPointF(b2_x, pt.y() - 6.0), QPointF(b2_x, pt.y() + 6.0))

    def _paint_self_relation(self, painter, box, rel):
        """자기 참조 루프 (예: 상위 카테고리)"""
        src_col_name = rel.get("src_column_name")
        start = box.right_anchor(src_col_name)
        end = box.left_anchor()

        offset = 24.0
        loop_right = box.x + box.width + offset
        loop_top = box.y - offset
        loop_left = box.x - offset

        pen = QPen(QColor("#94A3B8"), 1.5, Qt.PenStyle.DashLine)
        painter.setPen(pen)

        path = QPainterPath()
        path.moveTo(start)
        path.lineTo(loop_right, start.y())
        path.lineTo(loop_right, loop_top)
        path.lineTo(loop_left, loop_top)
        path.lineTo(loop_left, end.y())
        path.lineTo(end)
        painter.drawPath(path)


class ErDiagramView(QGraphicsView):
    """표준 ERD 그래픽 인터랙션 뷰"""

    table_double_clicked = pyqtSignal(str)

    def __init__(self, db_mgr, parent=None):
        super().__init__(parent)
        self.db_mgr = db_mgr
        self.show_self_ref = True
        self._dragging_table = None
        self._drag_offset = QPointF(0, 0)
        self._panning = False
        self._pan_start = None

        self._build_scene()

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.TextAntialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setBackgroundBrush(QBrush(QColor("#F8FAFC")))
        self.setStyleSheet("QGraphicsView { background-color: #F8FAFC; border: none; }")

    def _build_scene(self):
        tables = self.db_mgr.get_all_tables_for_mapping()
        relations = self.db_mgr.get_all_relations()

        fk_map = defaultdict(set)
        for rel in relations:
            src_t = rel.get("src_table_name")
            src_c = rel.get("src_column_name")
            if src_t and src_c:
                fk_map[src_t].add(src_c)

        boxes = []
        for t in tables:
            t_dict = dict(t)
            t_name = t_dict.get("table_name", "")
            t_ko = t_dict.get("table_ko_name", "")
            cols = self.db_mgr.get_table_columns(t_name)
            b = ErdTableBox(t_name, t_ko, cols, fk_map.get(t_name, set()))
            boxes.append(b)

        # 저장된 레이아웃 복원
        saved = self.db_mgr.get_setting("erd_layout_v2", "")
        has_saved = False
        if saved:
            try:
                layout = json.loads(saved)
                has_saved = bool(layout)
                for box in boxes:
                    pos = layout.get(box.table_name)
                    if pos:
                        box.x = float(pos[0])
                        box.y = float(pos[1])
            except Exception:
                has_saved = False

        try:
            self.show_self_ref = self.db_mgr.get_setting("erd_show_self_ref", "1") == "1"
        except Exception:
            self.show_self_ref = True

        self.canvas = ErdCanvasItem(boxes, relations, show_self_ref=self.show_self_ref)
        if not has_saved:
            self.canvas.auto_layout()

        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(self.canvas.boundingRect())
        self._scene.addItem(self.canvas)
        self.setScene(self._scene)

    def set_show_self_ref(self, enabled):
        self.show_self_ref = bool(enabled)
        if self.canvas is not None:
            self.canvas.show_self_ref = self.show_self_ref
            self._save_display_settings()
            self._refresh()

    def set_show_compact(self, compact):
        """컴팩트 모드 토글 (PK/FK만 표시)"""
        if self.canvas is not None:
            self.canvas.set_show_compact(compact)
            self._refresh()

    def set_show_ko_columns(self, show_ko):
        """컬럼 논리명(한글) 표시 토글"""
        if self.canvas is not None:
            self.canvas.set_show_ko_columns(show_ko)
            self._refresh()

    def focus_table(self, table_name):
        """특정 테이블을 캔버스 중앙으로 스크롤 및 하이라이트"""
        box = self.canvas.boxes.get(table_name)
        if box is not None:
            self.canvas.set_selected_table(table_name)
            self.centerOn(box.rect().center())
            self._refresh()

    def _save_display_settings(self):
        try:
            self.db_mgr.set_setting("erd_show_self_ref", "1" if self.show_self_ref else "0")
        except Exception:
            pass

    def _refresh(self):
        self.canvas.prepareGeometryChange()
        self.canvas.update()
        self._scene.setSceneRect(self.canvas.boundingRect())

    def _save_layout(self):
        try:
            layout = {
                b.table_name: [float(b.x), float(b.y)]
                for b in self.canvas.boxes.values()
            }
            self.db_mgr.set_setting("erd_layout_v2", json.dumps(layout))
        except Exception:
            pass

    # ---------- 마우스 및 제스처 인터랙션 ----------
    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())

        # 우클릭 또는 휠 클릭 시 화면 패닝(화면 이동)
        if event.button() in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton):
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            event.accept()
            return

        # 좌클릭: 테이블 클릭 선택 및 드래그 시작
        clicked_box = None
        for box in self.canvas.boxes.values():
            if box.contains(scene_pos):
                clicked_box = box
                break

        if clicked_box is not None:
            self._dragging_table = clicked_box
            self._drag_offset = QPointF(scene_pos.x() - clicked_box.x, scene_pos.y() - clicked_box.y)
            self.canvas.set_selected_table(clicked_box.table_name)
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            self._refresh()
        else:
            # 빈 곳 클릭 시 선택 해제
            if self.canvas.selected_table is not None:
                self.canvas.set_selected_table(None)
                self._refresh()

        event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging_table is not None:
            scene_pos = self.mapToScene(event.pos())
            box = self._dragging_table
            box.x = max(0.0, scene_pos.x() - self._drag_offset.x())
            box.y = max(0.0, scene_pos.y() - self._drag_offset.y())
            self._refresh()
            event.accept()
            return

        if self._panning and self._pan_start is not None:
            delta = event.pos() - self._pan_start
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._pan_start = event.pos()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging_table is not None:
            self._save_layout()
            self._dragging_table = None
            self.unsetCursor()
            event.accept()
            return

        if self._panning:
            self._panning = False
            self.unsetCursor()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        for box in self.canvas.boxes.values():
            if box.contains(scene_pos):
                self.table_double_clicked.emit(box.table_name)
                break
        event.accept()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else (1.0 / 1.15)
        self.scale(factor, factor)
        event.accept()

    # ---------- 툴바 명령 메서드 ----------
    def zoom_in(self):
        self.scale(1.2, 1.2)

    def zoom_out(self):
        self.scale(1.0 / 1.2, 1.0 / 1.2)

    def reset_zoom(self):
        self.resetTransform()
        self._refresh()

    def reset_layout(self):
        self.canvas.auto_layout()
        self._refresh()
        self._save_layout()
        self.fitInView(self.canvas.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def fit_in_view(self):
        self.fitInView(self.canvas.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def export_png(self, path):
        scene = self._scene
        br = scene.itemsBoundingRect()
        if br.isNull():
            br = self.canvas.boundingRect()

        size = br.size().toSize()
        img = QImage(max(size.width(), 1), max(size.height(), 1), QImage.Format.Format_ARGB32)
        img.fill(QColor("#F8FAFC"))

        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        scene.render(painter, QRectF(), br)
        painter.end()
        return img.save(path)
