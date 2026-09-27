import { Component, onWillStart, useExternalListener, xml } from '@odoo/owl';
import { download } from '@web/core/network/download';
import { registry } from '@web/core/registry';
import { useFileViewer } from '@web/core/file_viewer/file_viewer_hook';
import { useService } from '@web/core/utils/hooks';
import { standardFieldProps } from '@web/views/fields/standard_field_props';
import { FormRenderer } from '@web/views/form/form_renderer';
import { formView } from '@web/views/form/form_view';
import { ExtractMixinFormRenderer } from "@iap_extract/components/manual_correction/form_renderer";

export function extractAttachmentIds(value) {
    return value?.records?.map((record) => record.resId) || (value ? [value[0]] : []);
}

export function openAttachment(attachment, attachments, fileViewer, downloadFile = download) {
    if (attachment.isViewable) {
        fileViewer.open(attachment, attachments);
    } else {
        downloadFile({ data: {}, url: attachment.downloadUrl });
    }
}

export function normalizeExtractedValue(value, boxType = "word") {
    if (value === undefined || value === null || value === false) {
        return "";
    }
    const text = typeof value === "object" ? value.display_name || value.name || value.toString() : String(value);
    const normalized = text.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
    if (boxType === "number") {
        const number = Number(normalized.replace(/,/g, "").replace(/[^\d.-]/g, ""));
        return Number.isFinite(number) ? String(number) : normalized.replace(/[^\d-]/g, "");
    }
    if (boxType === "date") {
        return normalized.replace(/\D/g, "");
    }
    return normalized.replace(/\s+/g, " ").replace(/[^\p{L}\p{N}]+/gu, "");
}

export function hasBoxGeometry(box) {
    return ["midX", "midY", "width", "height"].every((key) => Number.isFinite(box?.[key])) &&
        box.width > 0 && box.width <= 1 && box.height > 0 && box.height <= 1 &&
        box.midX - box.width / 2 >= 0 && box.midX + box.width / 2 <= 1 &&
        box.midY - box.height / 2 >= 0 && box.midY + box.height / 2 <= 1;
}

export function findMatchingBox(boxesByPage, value, boxType) {
    const target = normalizeExtractedValue(value, boxType);
    if (!target) {
        return;
    }
    for (const pageBoxes of Object.values(boxesByPage || {})) {
        const match = pageBoxes.find(
            (box) => hasBoxGeometry(box) && normalizeExtractedValue(box.text, boxType) === target
        );
        if (match) {
            return match;
        }
    }
}

export class LogisticsAttachmentViewerField extends Component {
    static props = { ...standardFieldProps };
    static template = xml`<div class="d-flex flex-wrap gap-2">
        <button t-foreach="attachments" t-as="attachment" t-key="attachment.id"
                type="button" class="btn btn-link p-0" t-on-click="() => open(attachment)">
            <t t-esc="attachment.name"/>
        </button>
    </div>`;

    setup() {
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.fileViewer = useFileViewer();
        this.attachments = [];
        onWillStart(async () => {
            const value = this.props.record.data[this.props.name];
            const ids = extractAttachmentIds(value);
            if (ids.length) {
                const data = await this.orm.call("is.attachment", "get_file_viewer_data", [ids]);
                this.attachments = data.map((attachment) => this.store.Attachment.insert(attachment));
            }
        });
    }

    open(attachment) {
        openAttachment(attachment, this.attachments, this.fileViewer);
    }
}

export class LogisticsDocumentFormRenderer extends ExtractMixinFormRenderer(FormRenderer) {
    setup() {
        super.setup();
        this.recordModel = "logistics.idp.document";
        this.highlightRequest = 0;
        useExternalListener(window, "click", (event) => {
            const fieldWidget = event.target.closest(".w_logistics_extracted_field");
            if (fieldWidget) {
                this.highlightExtractedValue(fieldWidget);
            }
        });
    }

    /**
     * @override ExtractMixinFormRenderer
     * Always enable interactive OCR bounding boxes and word layer on the document preview
     */
    shouldRenderBoxes() {
        return Boolean(
            this.props.record.data.attachment_id ||
            this.props.record.data.extract_attachment_id
        );
    }

    onFocusFieldWidget(fieldWidget) {
        if (!fieldWidget.classList.contains("w_logistics_extracted_field")) {
            return super.onFocusFieldWidget(fieldWidget);
        }
        this.highlightExtractedValue(fieldWidget);
    }

    resetActiveField() {
        if (this.highlightedBox) {
            this.highlightedBox.isHighlighted = false;
            this.highlightedBox = undefined;
        }
        super.resetActiveField();
    }

    getExtractedFieldValue(fieldWidget, fullFieldName) {
        if (!fullFieldName.includes(".")) {
            return this.props.record.data[fullFieldName];
        }
        const [parentField, fieldName] = fullFieldName.split(".");
        const row = fieldWidget.closest("tr");
        const rowIndex = Array.from(row.parentElement.children).indexOf(row);
        return this.props.record.data[parentField].records[rowIndex]?.data[fieldName];
    }

    async highlightExtractedValue(fieldWidget) {
        const request = ++this.highlightRequest;
        const fullFieldName = this.getFullFieldName(fieldWidget);
        const boxType = this.getBoxType(fullFieldName);
        const value = this.getExtractedFieldValue(fieldWidget, fullFieldName);
        this.resetActiveField();
        if (!boxType) {
            return;
        }
        this.activeField = fullFieldName;
        this.activeFieldEl = fieldWidget;
        this.activeBoxType = boxType;
        if (this.recordId !== this.props.record.resId) {
            this.boxes = await this.orm.call(this.recordModel, "get_boxes", [this.props.record.resId]);
            this.recordId = this.props.record.resId;
        }
        if (request !== this.highlightRequest) {
            return;
        }
        const match = findMatchingBox(this.boxes[boxType], value, boxType);
        for (const boxesByPage of Object.values(this.boxes)) {
            for (const pageBoxes of Object.values(boxesByPage)) {
                pageBoxes.forEach((box) => box.isHighlighted = false);
            }
        }
        if (match) {
            match.isHighlighted = true;
            this.highlightedBox = match;
        }
        this.state.visibleBoxes = Object.fromEntries(
            Object.entries(this.boxes[boxType] || {}).map(([page, boxes]) => [
                page,
                boxes.filter(hasBoxGeometry),
            ])
        );
        const win = this.mailPopoutService.externalWindow || window;
        const attachment = win.document.querySelector(".w-mail-Attachment iframe") ||
            win.document.getElementById("attachment_img");
        if (attachment) {
            this.destroyBoxLayers();
            await this.renderBoxLayers(attachment);
        }
        if (match) {
            this.scrollToBox(match);
        }
    }

    scrollToBox(box) {
        const win = this.mailPopoutService.externalWindow || window;
        const iframe = win.document.querySelector(".w-mail-Attachment iframe");
        const page = iframe?.contentDocument?.querySelector(`.page[data-page-number="${Number(box.page) + 1}"]`);
        page?.scrollIntoView({ block: "center" });
        page?.querySelector(`.w_extract_mixin_box[data-id="${box.id}"]`)?.scrollIntoView({ block: "center" });
    }
}

registry.category("fields").add("logistics_attachment_viewer", {
    component: LogisticsAttachmentViewerField,
    supportedTypes: ["many2one", "many2many"],
});

registry.category("views").add("logistics_idp_document_form", {
    ...formView,
    Renderer: LogisticsDocumentFormRenderer,
});
