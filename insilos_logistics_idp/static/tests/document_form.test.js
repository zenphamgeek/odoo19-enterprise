import { expect, test } from '@odoo/hoot';
import { registry } from '@web/core/registry';
import { FormRenderer } from '@web/views/form/form_renderer';
import {
    extractAttachmentIds,
    findMatchingBox,
    LogisticsAttachmentViewerField,
    LogisticsDocumentFormRenderer,
    normalizeExtractedValue,
    openAttachment,
} from "@insilos_logistics_idp/document/document_form";

test("attachment field adapter extracts relational ids", () => {
    expect(extractAttachmentIds({ records: [{ resId: 4 }, { resId: 9 }] })).toEqual([4, 9]);
    expect(extractAttachmentIds([7, "invoice.pdf"])).toEqual([7]);
    expect(extractAttachmentIds(false)).toEqual([]);
});

test("extracted value normalization supports words, numbers, and dates", () => {
    expect(normalizeExtractedValue("  Hóa đơn INV-01 ")).toBe("hoa don inv01");
    expect(normalizeExtractedValue("1,234.50", "number")).toBe("1234.5");
    expect(normalizeExtractedValue("2026-09-22", "date")).toBe("20260922");
});

test("box matching is deterministic and rejects empty geometry", () => {
    const boxes = {
        0: [
            { id: 1, text: "INV-01", midX: 0.1, midY: 0.1, width: 0, height: 0.1 },
            { id: 2, text: "INV-01", midX: 0.2, midY: 0.2, width: 0.1, height: 0.1 },
            { id: 3, text: "INV-01", midX: 0.3, midY: 0.3, width: 0.1, height: 0.1 },
        ],
    };
    expect(findMatchingBox(boxes, "inv 01", "word").id).toBe(2);
    expect(findMatchingBox(boxes, "", "word")).toBe(undefined);
    expect(findMatchingBox({ 0: [boxes[0][0]] }, "INV-01", "word")).toBe(undefined);
    expect(findMatchingBox({ 0: [{ ...boxes[0][1], midX: 0.98 }] }, "INV-01", "word")).toBe(undefined);
});

test("review station keeps empty and non-matching fields active with all valid candidates", async () => {
    const valid = (id, text) => ({ id, text, page: 0, midX: 0.2, midY: 0.2, width: 0.1, height: 0.1 });
    const invalid = { ...valid(3, "broken"), width: 0 };
    const fieldWidget = {};
    const renderer = {
        highlightRequest: 0,
        recordId: 7,
        props: { record: { resId: 7 } },
        boxes: { word: { 0: [valid(1, "INV-01"), valid(2, "ALT-02"), invalid] } },
        state: {},
        mailPopoutService: {},
        getFullFieldName: () => "extracted_doc_number",
        getBoxType: () => "word",
        getExtractedFieldValue: () => "",
        resetActiveField() {
            this.activeField = undefined;
            this.activeFieldEl = undefined;
            this.activeBoxType = undefined;
        },
        scrollToBox: () => expect.step("scroll"),
    };

    await LogisticsDocumentFormRenderer.prototype.highlightExtractedValue.call(renderer, fieldWidget);
    expect(renderer.activeField).toBe("extracted_doc_number");
    expect(renderer.activeFieldEl).toBe(fieldWidget);
    expect(renderer.activeBoxType).toBe("word");
    expect(renderer.state.visibleBoxes[0].map(({ id }) => id)).toEqual([1, 2]);
    expect.verifySteps([]);

    renderer.getExtractedFieldValue = () => "missing";
    await LogisticsDocumentFormRenderer.prototype.highlightExtractedValue.call(renderer, fieldWidget);
    expect(renderer.state.visibleBoxes[0].map(({ id }) => id)).toEqual([1, 2]);
    expect(renderer.highlightedBox).toBe(undefined);
    expect.verifySteps([]);

    renderer.getExtractedFieldValue = () => "INV 01";
    await LogisticsDocumentFormRenderer.prototype.highlightExtractedValue.call(renderer, fieldWidget);
    expect(renderer.state.visibleBoxes[0].map(({ id }) => id)).toEqual([1, 2]);
    expect(renderer.highlightedBox.id).toBe(1);
    expect(renderer.boxes.word[0][1].isHighlighted).toBe(false);
    expect.verifySteps(["scroll"]);
});

test("attachment field adapter delegates every intake MIME to native viewer or download", () => {
    const gallery = [
        { id: 1, mimetype: "application/pdf", isViewable: true },
        { id: 2, mimetype: "image/png", isViewable: true },
        { id: 3, mimetype: "image/jpeg", isViewable: true },
        { id: 4, mimetype: "text/csv", isViewable: false },
        { id: 5, mimetype: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", isViewable: false },
        { id: 6, mimetype: "message/rfc822", isViewable: false },
        { id: 7, mimetype: "application/json", isViewable: false },
    ].map((attachment) => ({ ...attachment, downloadUrl: `/web/content/${attachment.id}?download=true` }));
    const opened = [];
    const downloaded = [];
    for (const attachment of gallery) {
        openAttachment(attachment, gallery, { open: (...args) => opened.push(args) }, (args) => downloaded.push(args));
    }
    expect(opened).toEqual(gallery.slice(0, 3).map((attachment) => [attachment, gallery]));
    expect(downloaded).toEqual(gallery.slice(3).map((attachment) => ({ data: {}, url: attachment.downloadUrl })));
});

test("native viewer field and form renderer stay wired in registries", () => {
    const field = registry.category("fields").get("logistics_attachment_viewer");
    const view = registry.category("views").get("logistics_idp_document_form");
    expect(field.component).toBe(LogisticsAttachmentViewerField);
    expect(field.supportedTypes).toEqual(["many2one", "many2many"]);
    expect(view.Renderer).toBe(LogisticsDocumentFormRenderer);
    expect(LogisticsDocumentFormRenderer.prototype).toBeInstanceOf(FormRenderer);
});
