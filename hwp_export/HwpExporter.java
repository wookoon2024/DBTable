import kr.dogfoot.hwplib.object.HWPFile;
import kr.dogfoot.hwplib.object.bodytext.Section;
import kr.dogfoot.hwplib.object.bodytext.control.ControlTable;
import kr.dogfoot.hwplib.object.bodytext.control.ControlType;
import kr.dogfoot.hwplib.object.bodytext.control.ctrlheader.CtrlHeaderGso;
import kr.dogfoot.hwplib.object.bodytext.control.ctrlheader.gso.*;
import kr.dogfoot.hwplib.object.bodytext.control.ctrlheader.sectiondefine.TextDirection;
import kr.dogfoot.hwplib.object.bodytext.control.gso.GsoControlType;
import kr.dogfoot.hwplib.object.bodytext.control.gso.ControlRectangle;
import kr.dogfoot.hwplib.object.bodytext.control.gso.shapecomponent.ShapeComponentNormal;
import kr.dogfoot.hwplib.object.bodytext.control.gso.shapecomponent.lineinfo.*;
import kr.dogfoot.hwplib.object.bodytext.control.gso.shapecomponent.shadowinfo.ShadowInfo;
import kr.dogfoot.hwplib.object.bodytext.control.gso.shapecomponent.shadowinfo.ShadowType;
import kr.dogfoot.hwplib.object.bodytext.control.gso.shapecomponenteach.ShapeComponentRectangle;
import kr.dogfoot.hwplib.object.bodytext.control.gso.textbox.LineChange;
import kr.dogfoot.hwplib.object.bodytext.control.gso.textbox.TextVerticalAlignment;
import kr.dogfoot.hwplib.object.bodytext.control.table.*;
import kr.dogfoot.hwplib.object.bodytext.paragraph.Paragraph;
import kr.dogfoot.hwplib.object.bodytext.paragraph.charshape.ParaCharShape;
import kr.dogfoot.hwplib.object.bodytext.paragraph.header.ParaHeader;
import kr.dogfoot.hwplib.object.bodytext.paragraph.lineseg.LineSegItem;
import kr.dogfoot.hwplib.object.bodytext.paragraph.lineseg.ParaLineSeg;
import kr.dogfoot.hwplib.object.bodytext.paragraph.text.ParaText;
import kr.dogfoot.hwplib.object.docinfo.BinData;
import kr.dogfoot.hwplib.object.docinfo.BorderFill;
import kr.dogfoot.hwplib.object.docinfo.CharShape;
import kr.dogfoot.hwplib.object.docinfo.FaceName;
import kr.dogfoot.hwplib.object.docinfo.bindata.BinDataCompress;
import kr.dogfoot.hwplib.object.docinfo.bindata.BinDataState;
import kr.dogfoot.hwplib.object.docinfo.bindata.BinDataType;
import kr.dogfoot.hwplib.object.docinfo.borderfill.BackSlashDiagonalShape;
import kr.dogfoot.hwplib.object.docinfo.borderfill.BorderThickness;
import kr.dogfoot.hwplib.object.docinfo.borderfill.BorderType;
import kr.dogfoot.hwplib.object.docinfo.borderfill.SlashDiagonalShape;
import kr.dogfoot.hwplib.object.docinfo.borderfill.fillinfo.FillInfo;
import kr.dogfoot.hwplib.object.docinfo.borderfill.fillinfo.ImageFill;
import kr.dogfoot.hwplib.object.docinfo.borderfill.fillinfo.ImageFillType;
import kr.dogfoot.hwplib.object.docinfo.borderfill.fillinfo.PatternFill;
import kr.dogfoot.hwplib.object.docinfo.borderfill.fillinfo.PatternType;
import kr.dogfoot.hwplib.object.docinfo.borderfill.fillinfo.PictureEffect;
import kr.dogfoot.hwplib.object.docinfo.charshape.UnderLineSort;
import kr.dogfoot.hwplib.tool.blankfilemaker.BlankFileMaker;
import kr.dogfoot.hwplib.writer.HWPWriter;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;

/**
 * 명령 스트림(텍스트 파일)을 읽어 hwplib으로 .hwp 파일을 생성한다.
 * Python(biz_guide_app.py)이 HTML을 파싱하여 명령 스트림을 만들고 이 프로그램을 호출한다.
 *
 * 명령 포맷 (구분자 '|', 텍스트/경로는 base64) :
 *   P                                                  본문 텍스트 문단 시작
 *   R|bold|italic|underline|sizePt|colorHex6|b64text   현재 문단에 텍스트 런 추가
 *   IMG|b64abspath|ext|wMM|hMM                          이미지 문단(단독)
 *   TBL|rows|cols                                       표 시작
 *   ROW                                                 행 시작
 *   CELL|b64text|bold|sizePt                            셀(단순 텍스트)
 *   ENDTBL                                              표 끝
 */
public class HwpExporter {
    static HWPFile hwp;
    static Section sec;
    static HashMap<String, Integer> charShapeCache = new HashMap<>();
    static int instanceSeq = 0x10000000;
    static final int BODY_WIDTH_MM = 160;
    static int[] curColWidths;

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("usage: HwpExporter <cmdFile> <outFile>");
            System.exit(2);
        }
        String cmdFile = args[0];
        String outFile = args[1];

        hwp = BlankFileMaker.make();
        sec = hwp.getBodyText().getSectionList().get(0);

        // 본문 기본 글꼴을 웹 에디터(맑은 고딕)와 동일하게 맞춘다.
        applyDefaultFont("맑은 고딕");

        List<String> lines = Files.readAllLines(Paths.get(cmdFile), StandardCharsets.UTF_8);

        Paragraph curText = null;
        int curRunCount = 0;

        ControlTable curTable = null;
        Row curRow = null;
        int curCols = 0;
        int curRowIdx = 0;
        int curColIdx = 0;
        int tblBorderCell = 0;

        for (String raw : lines) {
            if (raw == null || raw.isEmpty()) continue;
            String[] t = raw.split("\\|", -1);
            String op = t[0];

            if (op.equals("P")) {
                if (curText != null) finalizeTextPara(curText, curRunCount);
                curText = sec.addNewParagraph();
                curRunCount = 0;
            } else if (op.equals("R")) {
                if (curText == null) {
                    curText = sec.addNewParagraph();
                    curRunCount = 0;
                }
                boolean bold = t[1].equals("1");
                boolean italic = t[2].equals("1");
                boolean underline = t[3].equals("1");
                int sizePt = parseIntDef(t[4], 10);
                int color = parseColor(t[5]);
                String text = b64(t[6]);
                if (text.isEmpty()) continue;
                if (curText.getText() == null) {
                    curText.createText();
                    curText.createCharShape();
                }
                int csId = getCharShape(bold, italic, underline, sizePt, color);
                int startPos = curText.getText().getCharList().size();
                curText.getText().addString(text);
                curText.getCharShape().addParaCharShape(startPos, csId);
                curRunCount++;
            } else if (op.equals("IMG")) {
                if (curText != null) { finalizeTextPara(curText, curRunCount); curText = null; }
                String path = b64(t[1]);
                String ext = t[2];
                int wmm = parseIntDef(t[3], 100);
                int hmm = parseIntDef(t[4], 75);
                Paragraph p = sec.addNewParagraph();
                p.createText();
                p.createCharShape();
                insertImage(p, path, ext, wmm, hmm);
                int csId = getCharShape(false, false, false, 10, 0);
                p.getCharShape().addParaCharShape(0, csId);
                finalizeParaCommon(p, p.getText().getCharList().size(), 1);
            } else if (op.equals("TBL")) {
                if (curText != null) { finalizeTextPara(curText, curRunCount); curText = null; }
                int rows = parseIntDef(t[1], 1);
                int cols = parseIntDef(t[2], 1);
                int[] colWidths = new int[cols];
                if (t.length > 3 && !t[3].isEmpty()) {
                    String[] parts = t[3].split(",");
                    for (int i = 0; i < cols; i++) {
                        if (i < parts.length) {
                            colWidths[i] = parseIntDef(parts[i], BODY_WIDTH_MM / cols);
                        } else {
                            colWidths[i] = BODY_WIDTH_MM / cols;
                        }
                    }
                } else {
                    for (int i = 0; i < cols; i++) {
                        colWidths[i] = BODY_WIDTH_MM / cols;
                    }
                }
                curColWidths = colWidths;
                Paragraph p = sec.addNewParagraph();
                p.createText();
                p.createCharShape();
                int csId = getCharShape(false, false, false, 11, 0);
                p.getCharShape().addParaCharShape(0, csId);
                curTable = startTable(p, rows, cols, colWidths);
                curCols = cols;
                curRowIdx = 0;
                tblBorderCell = borderFillForCell();
                finalizeParaCommon(p, p.getText().getCharList().size(), 1);
            } else if (op.equals("ROW")) {
                if (curTable == null) continue;
                curRow = curTable.addNewRow();
                curColIdx = 0;
                curRowIdx = curTable.getRowList().size() - 1;
            } else if (op.equals("CELL")) {
                if (curTable == null || curRow == null) continue;
                String text = b64(t[1]);
                boolean bold = t.length > 2 && t[2].equals("1");
                int sizePt = t.length > 3 ? parseIntDef(t[3], 11) : 11;
                addCell(curRow, curColIdx, curRowIdx, curCols, curColWidths, text, bold, sizePt, tblBorderCell);
                curColIdx++;
            } else if (op.equals("ENDTBL")) {
                // 표 다음에 빈 본문 문단 하나 (한글에서 표 뒤 커서 위치)
                Paragraph p = sec.addNewParagraph();
                emptyParagraph(p);
                curTable = null;
                curRow = null;
            }
        }
        if (curText != null) finalizeTextPara(curText, curRunCount);

        HWPWriter.toFile(hwp, outFile);
        System.out.println("OK:" + outFile);
    }

    // ---------- 문단 ----------
    static void finalizeTextPara(Paragraph p, int runCount) {
        if (runCount == 0 || p.getText() == null) {
            emptyParagraph(p);
            return;
        }
        int charCount = p.getText().getCharList().size();
        finalizeParaCommon(p, charCount, runCount);
    }

    // 빈 문단: 텍스트 레코드 없이 charShape/lineSeg만 (writer가 빈 텍스트로 인식)
    static void emptyParagraph(Paragraph p) {
        if (p.getCharShape() == null) p.createCharShape();
        if (p.getCharShape().getPositonShapeIdPairList().isEmpty()) {
            int csId = getCharShape(false, false, false, 10, 0);
            p.getCharShape().addParaCharShape(0, csId);
        }
        finalizeParaCommon(p, 0, 1);
    }

    static void finalizeParaCommon(Paragraph p, int charCount, int charShapeCount) {
        ParaHeader ph = p.getHeader();
        ph.setLastInList(true);
        ph.setParaShapeId(1);
        ph.setStyleId((short) 1);
        ph.setCharacterCount(charCount);
        ph.getDivideSort().setDivideSection(false);
        ph.getDivideSort().setDivideMultiColumn(false);
        ph.getDivideSort().setDividePage(false);
        ph.getDivideSort().setDivideColumn(false);
        ph.setCharShapeCount(charShapeCount);
        ph.setRangeTagCount(0);
        ph.setLineAlignCount(1);
        ph.setInstanceID(instanceSeq++);
        ph.setIsMergedByTrack(0);

        p.createLineSeg();
        ParaLineSeg pls = p.getLineSeg();
        LineSegItem lsi = pls.addNewLineSegItem();
        lsi.setTextStartPosition(0);
        lsi.setLineVerticalPosition(0);
        lsi.setLineHeight(ptToLineHeight(10.0));
        lsi.setTextPartHeight(ptToLineHeight(10.0));
        lsi.setDistanceBaseLineToLineVerticalPosition(ptToLineHeight(10.0 * 0.85));
        lsi.setLineSpace(ptToLineHeight(4.0));
        lsi.setStartPositionFromColumn(0);
        lsi.setSegmentWidth((int) mmToHwp(BODY_WIDTH_MM));
        lsi.getTag().setFirstSegmentAtLine(true);
        lsi.getTag().setLastSegmentAtLine(true);
    }

    // ---------- 기본 글꼴 ----------
    // BlankFileMaker가 만든 모든 글꼴(7개 언어 목록)의 이름을 지정 글꼴로 교체한다.
    // 모든 텍스트가 동일 face id를 쓰므로 이렇게 하면 본문 전체가 해당 글꼴로 표시된다.
    static void applyDefaultFont(String name) {
        try {
            java.util.ArrayList<java.util.ArrayList<FaceName>> lists = new java.util.ArrayList<>();
            lists.add(hwp.getDocInfo().getHangulFaceNameList());
            lists.add(hwp.getDocInfo().getEnglishFaceNameList());
            lists.add(hwp.getDocInfo().getHanjaFaceNameList());
            lists.add(hwp.getDocInfo().getJapaneseFaceNameList());
            lists.add(hwp.getDocInfo().getEtcFaceNameList());
            lists.add(hwp.getDocInfo().getSymbolFaceNameList());
            lists.add(hwp.getDocInfo().getUserFaceNameList());
            for (java.util.ArrayList<FaceName> l : lists) {
                if (l == null) continue;
                for (FaceName fn : l) {
                    if (fn != null) fn.setName(name);
                }
            }
        } catch (Exception e) { /* 글꼴 교체 실패 시 기본값 유지 */ }
    }

    // ---------- 글자모양 ----------
    static int getCharShape(boolean bold, boolean italic, boolean underline, int sizePt, int color) {
        String key = bold + "_" + italic + "_" + underline + "_" + sizePt + "_" + color;
        Integer cached = charShapeCache.get(key);
        if (cached != null) return cached;

        CharShape cs = hwp.getDocInfo().addNewCharShape();
        cs.getFaceNameIds().setForAll(1); // 함초롬바탕
        cs.getRatios().setForAll((short) 100);
        cs.getCharSpaces().setForAll((byte) 0);
        cs.getRelativeSizes().setForAll((short) 100);
        cs.getCharOffsets().setForAll((byte) 0);
        cs.setBaseSize(sizePt * 100);
        cs.getProperty().setValue(0);
        cs.getProperty().setBold(bold);
        cs.getProperty().setItalic(italic);
        cs.getProperty().setUnderLineSort(underline ? UnderLineSort.Bottom : UnderLineSort.None);
        cs.setShadowGap1((byte) 10);
        cs.setShadowGap2((byte) 10);
        cs.getCharColor().setValue(color);
        cs.getUnderLineColor().setValue(color);
        cs.getShadeColor().setValue(-1);
        cs.getShadowColor().setValue(11711154);
        cs.setBorderFillId(2);
        cs.getStrikeLineColor().setValue(0);

        int id = hwp.getDocInfo().getCharShapeList().size() - 1;
        charShapeCache.put(key, id);
        return id;
    }

    // ---------- 이미지 ----------
    static void insertImage(Paragraph para, String imagePath, String ext, int wMM, int hMM) throws Exception {
        BinDataCompress compress = BinDataCompress.ByStorageDefault;
        int streamIndex = hwp.getBinData().getEmbeddedBinaryDataList().size() + 1;
        String streamName = "Bin" + String.format("%04X", streamIndex) + "." + ext;
        byte[] fileBinary = Files.readAllBytes(Paths.get(imagePath));
        hwp.getBinData().addNewEmbeddedBinaryData(streamName, fileBinary, compress);

        BinData bd = new BinData();
        bd.getProperty().setType(BinDataType.Embedding);
        bd.getProperty().setCompress(compress);
        bd.getProperty().setState(BinDataState.NotAccess);
        bd.setBinDataID(streamIndex);
        bd.setExtensionForEmbedding(ext);
        hwp.getDocInfo().getBinDataList().add(bd);
        int binDataID = hwp.getDocInfo().getBinDataList().size();

        para.getText().addExtendCharForGSO();
        ControlRectangle rect = (ControlRectangle) para.addNewGsoControl(GsoControlType.Rectangle);

        CtrlHeaderGso hdr = rect.getHeader();
        GsoHeaderProperty prop = hdr.getProperty();
        prop.setLikeWord(true); // 글자처럼 취급 → 텍스트 흐름 따라 인라인 배치(겹침 방지)
        prop.setApplyLineSpace(false);
        prop.setVertRelTo(VertRelTo.Para);
        prop.setVertRelativeArrange(RelativeArrange.TopOrLeft);
        prop.setHorzRelTo(HorzRelTo.Para);
        prop.setHorzRelativeArrange(RelativeArrange.TopOrLeft);
        prop.setVertRelToParaLimit(true);
        prop.setAllowOverlap(true);
        prop.setWidthCriterion(WidthCriterion.Absolute);
        prop.setHeightCriterion(HeightCriterion.Absolute);
        prop.setProtectSize(false);
        prop.setTextFlowMethod(TextFlowMethod.FitWithText);
        prop.setTextHorzArrange(TextHorzArrange.BothSides);
        prop.setObjectNumberSort(ObjectNumberSort.Figure);
        hdr.setyOffset(0);
        hdr.setxOffset(0);
        hdr.setWidth(mmToHwp(wMM));
        hdr.setHeight(mmToHwp(hMM));
        hdr.setzOrder(0);
        hdr.setOutterMarginLeft(0);
        hdr.setOutterMarginRight(0);
        hdr.setOutterMarginTop(0);
        hdr.setOutterMarginBottom(0);
        hdr.setInstanceId(instanceSeq++);
        hdr.setPreventPageDivide(false);
        hdr.getExplanation().setBytes(null);

        ShapeComponentNormal sc = (ShapeComponentNormal) rect.getShapeComponent();
        sc.getProperty().setRotateWithImage(true);
        sc.setOffsetX(0);
        sc.setOffsetY(0);
        sc.setGroupingCount(0);
        sc.setLocalFileVersion(1);
        sc.setWidthAtCreate((int) mmToHwp(wMM));
        sc.setHeightAtCreate((int) mmToHwp(hMM));
        sc.setWidthAtCurrent((int) mmToHwp(wMM));
        sc.setHeightAtCurrent((int) mmToHwp(hMM));
        sc.setRotateAngle(0);
        sc.setRotateXCenter((int) mmToHwp(wMM / 2));
        sc.setRotateYCenter((int) mmToHwp(hMM / 2));

        sc.createLineInfo();
        LineInfo li = sc.getLineInfo();
        li.getProperty().setLineEndShape(LineEndShape.Flat);
        li.getProperty().setStartArrowShape(LineArrowShape.None);
        li.getProperty().setStartArrowSize(LineArrowSize.MiddleMiddle);
        li.getProperty().setEndArrowShape(LineArrowShape.None);
        li.getProperty().setEndArrowSize(LineArrowSize.MiddleMiddle);
        li.getProperty().setFillStartArrow(true);
        li.getProperty().setFillEndArrow(true);
        li.getProperty().setLineType(LineType.None);
        li.setOutlineStyle(OutlineStyle.Normal);
        li.setThickness(0);
        li.getColor().setValue(0);

        sc.createFillInfo();
        FillInfo fi = sc.getFillInfo();
        fi.getType().setPatternFill(false);
        fi.getType().setImageFill(true);
        fi.getType().setGradientFill(false);
        fi.createImageFill();
        ImageFill imgF = fi.getImageFill();
        imgF.setImageFillType(ImageFillType.FitSize);
        imgF.getPictureInfo().setBrightness((byte) 0);
        imgF.getPictureInfo().setContrast((byte) 0);
        imgF.getPictureInfo().setEffect(PictureEffect.RealPicture);
        imgF.getPictureInfo().setBinItemID(binDataID);

        sc.createShadowInfo();
        ShadowInfo si = sc.getShadowInfo();
        si.setType(ShadowType.None);
        si.getColor().setValue(0xc4c4c4);
        si.setOffsetX(283);
        si.setOffsetY(283);
        si.setTransparent((short) 0);

        sc.setMatrixsNormal();

        ShapeComponentRectangle scr = rect.getShapeComponentRectangle();
        scr.setRoundRate((byte) 0);
        scr.setX1(0);
        scr.setY1(0);
        scr.setX2((int) mmToHwp(wMM));
        scr.setY2(0);
        scr.setX3((int) mmToHwp(wMM));
        scr.setY3((int) mmToHwp(hMM));
        scr.setX4(0);
        scr.setY4((int) mmToHwp(hMM));
    }

    // ---------- 표 ----------
    static ControlTable startTable(Paragraph para, int rows, int cols, int[] colWidths) {
        para.getText().addExtendCharForTable();
        ControlTable table = (ControlTable) para.addNewControl(ControlType.Table);

        CtrlHeaderGso ch = table.getHeader();
        ch.getProperty().setLikeWord(true); // 글자처럼 취급
        ch.getProperty().setApplyLineSpace(false);
        ch.getProperty().setVertRelTo(VertRelTo.Para);
        ch.getProperty().setVertRelativeArrange(RelativeArrange.TopOrLeft);
        ch.getProperty().setHorzRelTo(HorzRelTo.Para);
        ch.getProperty().setHorzRelativeArrange(RelativeArrange.TopOrLeft);
        ch.getProperty().setVertRelToParaLimit(false);
        ch.getProperty().setAllowOverlap(false);
        ch.getProperty().setWidthCriterion(WidthCriterion.Absolute);
        ch.getProperty().setHeightCriterion(HeightCriterion.Absolute);
        ch.getProperty().setProtectSize(false);
        ch.getProperty().setTextFlowMethod(TextFlowMethod.FitWithText);
        ch.getProperty().setTextHorzArrange(TextHorzArrange.BothSides);
        ch.getProperty().setObjectNumberSort(ObjectNumberSort.Table);
        int totalW = 0;
        for (int w : colWidths) totalW += w;
        ch.setxOffset(0);
        ch.setyOffset(0);
        ch.setWidth(mmToHwp(totalW));
        ch.setHeight(mmToHwp(10 * rows));
        ch.setzOrder(0);
        ch.setOutterMarginLeft(0);
        ch.setOutterMarginRight(0);
        ch.setOutterMarginTop(0);
        ch.setOutterMarginBottom(0);
        ch.setInstanceId(instanceSeq++);

        Table tr = table.getTable();
        tr.getProperty().setDivideAtPageBoundary(DivideAtPageBoundary.DivideByCell);
        tr.getProperty().setAutoRepeatTitleRow(false);
        tr.setRowCount(rows);
        tr.setColumnCount(cols);
        tr.setCellSpacing(0);
        tr.setLeftInnerMargin(0);
        tr.setRightInnerMargin(0);
        tr.setTopInnerMargin(0);
        tr.setBottomInnerMargin(0);
        tr.setBorderFillId(borderFillForTableOutline());
        for (int i = 0; i < rows; i++) tr.getCellCountOfRowList().add(cols);
        return table;
    }

    static void addCell(Row row, int colIdx, int rowIdx, int cols, int[] colWidths, String text, boolean bold, int sizePt, int borderFillId) {
        Cell cell = row.addNewCell();
        int colW = colWidths[colIdx];

        ListHeaderForCell lh = cell.getListHeader();
        lh.setParaCount(1);
        lh.getProperty().setTextDirection(TextDirection.Horizontal);
        lh.getProperty().setLineChange(LineChange.Normal);
        lh.getProperty().setTextVerticalAlignment(TextVerticalAlignment.Center);
        lh.getProperty().setProtectCell(false);
        lh.getProperty().setEditableAtFormMode(false);
        lh.setColIndex(colIdx);
        lh.setRowIndex(rowIdx);
        lh.setColSpan(1);
        lh.setRowSpan(1);
        lh.setWidth(mmToHwp(colW));
        lh.setHeight(mmToHwp(10));
        lh.setLeftMargin(141);
        lh.setRightMargin(141);
        lh.setTopMargin(141);
        lh.setBottomMargin(141);
        lh.setBorderFillId(borderFillId);
        lh.setTextWidth(mmToHwp(colW) - 282);
        lh.setFieldName("");

        Paragraph p = cell.getParagraphList().addNewParagraph();
        int charCount = 0;
        if (text != null && !text.isEmpty()) {
            p.createText();
            try { p.getText().addString(text); } catch (Exception e) {}
            charCount = p.getText().getCharList().size();
        }
        p.createCharShape();
        int csId = getCharShape(bold, false, false, sizePt, 0);
        p.getCharShape().addParaCharShape(0, csId);

        ParaHeader ph = p.getHeader();
        ph.setLastInList(true);
        ph.setParaShapeId(1);
        ph.setStyleId((short) 1);
        ph.setCharacterCount(charCount);
        ph.getDivideSort().setDivideSection(false);
        ph.getDivideSort().setDivideMultiColumn(false);
        ph.getDivideSort().setDividePage(false);
        ph.getDivideSort().setDivideColumn(false);
        ph.setCharShapeCount(1);
        ph.setRangeTagCount(0);
        ph.setLineAlignCount(1);
        ph.setInstanceID(instanceSeq++);
        ph.setIsMergedByTrack(0);

        p.createLineSeg();
        ParaLineSeg pls = p.getLineSeg();
        LineSegItem lsi = pls.addNewLineSegItem();
        lsi.setTextStartPosition(0);
        lsi.setLineVerticalPosition(0);
        lsi.setLineHeight(ptToLineHeight(sizePt));
        lsi.setTextPartHeight(ptToLineHeight(sizePt));
        lsi.setDistanceBaseLineToLineVerticalPosition(ptToLineHeight(sizePt * 0.85));
        lsi.setLineSpace(ptToLineHeight(4.0));
        lsi.setStartPositionFromColumn(0);
        lsi.setSegmentWidth((int) mmToHwp(colW));
        lsi.getTag().setFirstSegmentAtLine(true);
        lsi.getTag().setLastSegmentAtLine(true);
    }

    static int borderFillForTableOutline() {
        BorderFill bf = newBorderFill(BorderType.None);
        return hwp.getDocInfo().getBorderFillList().size();
    }

    static int borderFillForCell() {
        BorderFill bf = newBorderFill(BorderType.Solid);
        return hwp.getDocInfo().getBorderFillList().size();
    }

    static BorderFill newBorderFill(BorderType type) {
        BorderFill bf = hwp.getDocInfo().addNewBorderFill();
        bf.getProperty().set3DEffect(false);
        bf.getProperty().setShadowEffect(false);
        bf.getProperty().setSlashDiagonalShape(SlashDiagonalShape.None);
        bf.getProperty().setBackSlashDiagonalShape(BackSlashDiagonalShape.None);
        setBorder(bf, type);
        bf.getFillInfo().getType().setPatternFill(true);
        bf.getFillInfo().createPatternFill();
        PatternFill pf = bf.getFillInfo().getPatternFill();
        pf.setPatternType(PatternType.None);
        pf.getBackColor().setValue(-1);
        pf.getPatternColor().setValue(0);
        return bf;
    }

    static void setBorder(BorderFill bf, BorderType type) {
        bf.getLeftBorder().setType(type);
        bf.getLeftBorder().setThickness(BorderThickness.MM0_5);
        bf.getLeftBorder().getColor().setValue(0x0);
        bf.getRightBorder().setType(type);
        bf.getRightBorder().setThickness(BorderThickness.MM0_5);
        bf.getRightBorder().getColor().setValue(0x0);
        bf.getTopBorder().setType(type);
        bf.getTopBorder().setThickness(BorderThickness.MM0_5);
        bf.getTopBorder().getColor().setValue(0x0);
        bf.getBottomBorder().setType(type);
        bf.getBottomBorder().setThickness(BorderThickness.MM0_5);
        bf.getBottomBorder().getColor().setValue(0x0);
        bf.getDiagonalBorder().setType(BorderType.None);
        bf.getDiagonalBorder().setThickness(BorderThickness.MM0_5);
        bf.getDiagonalBorder().getColor().setValue(0x0);
    }

    // ---------- 유틸 ----------
    static String b64(String s) {
        if (s == null || s.isEmpty()) return "";
        return new String(Base64.getDecoder().decode(s), StandardCharsets.UTF_8);
    }

    static int parseIntDef(String s, int def) {
        try { return (int) Math.round(Double.parseDouble(s.trim())); } catch (Exception e) { return def; }
    }

    static int parseColor(String hex6) {
        // "rrggbb" -> hwp COLORREF(0x00BBGGRR)
        try {
            if (hex6.startsWith("#")) hex6 = hex6.substring(1);
            if (hex6.length() != 6) return 0;
            int r = Integer.parseInt(hex6.substring(0, 2), 16);
            int g = Integer.parseInt(hex6.substring(2, 4), 16);
            int b = Integer.parseInt(hex6.substring(4, 6), 16);
            return r | (g << 8) | (b << 16);
        } catch (Exception e) { return 0; }
    }

    static long mmToHwp(double mm) {
        return (long) (mm * 72000.0f / 254.0f + 0.5f);
    }

    static int ptToLineHeight(double pt) {
        return (int) (pt * 100.0f);
    }
}
