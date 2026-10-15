import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";

const textMimeTypePattern = /^text\//;
const additionalMimeTypes = ["application/xml"];
const excludedMimeTypes = ["text/html", "text/csv"];

function renderMarkdownToHtml(md) {
    let html = (md || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Code blocks
    html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_m, _lang, code) => {
        return `<pre class="md-code-block"><code>${code.trim()}</code></pre>`;
    });

    // Tables
    html = html.replace(
        /^(\|.+\|[ \t]*\n\|[ \t:|-]+\|[ \t]*\n(?:\|.+[ \t]*\n?)+)/gm,
        (tableBlock) => {
            const lines = tableBlock
                .trim()
                .split("\n")
                .map((l) => l.trim())
                .filter(Boolean);
            if (lines.length < 2) {
                return tableBlock;
            }
            const parseCells = (row) =>
                row
                    .replace(/^\||\|$/g, "")
                    .split("|")
                    .map((c) => c.trim());
            const headers = parseCells(lines[0]);
            const bodyLines = lines.slice(2);
            const thead = `<thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>`;
            const tbody = `<tbody>${bodyLines
                .map((r) => `<tr>${parseCells(r).map((c) => `<td>${c}</td>`).join("")}</tr>`)
                .join("")}</tbody>`;
            return `<div class="table-wrap"><table>${thead}${tbody}</table></div>`;
        }
    );

    // Headings
    html = html
        .replace(/^#### (.*$)/gm, "<h4>$1</h4>")
        .replace(/^### (.*$)/gm, "<h3>$1</h3>")
        .replace(/^## (.*$)/gm, "<h2>$1</h2>")
        .replace(/^# (.*$)/gm, "<h1>$1</h1>");

    // Blockquotes & Horizontal rules
    html = html
        .replace(/^&gt; (.*$)/gm, "<blockquote>$1</blockquote>")
        .replace(/^---$/gm, "<hr/>");

    // Bold, Italic, Inline code
    html = html
        .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
        .replace(/`([^`\n]+)`/g, '<code class="md-inline-code">$1</code>');

    // Unordered list items
    html = html.replace(/^[ \t]*[-*] (.*$)/gm, "<li>$1</li>");
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, "<ul>$1</ul>");

    // Paragraphs for remaining lines
    html = html
        .split("\n\n")
        .map((block) => {
            const trimmed = block.trim();
            if (!trimmed) {
                return "";
            }
            if (/^<(h[1-4]|pre|div|ul|blockquote|hr)/i.test(trimmed)) {
                return trimmed;
            }
            return `<p>${trimmed.replace(/\n/g, "<br/>")}</p>`;
        })
        .join("\n");

    return html;
}

/** @type {import("models").Attachment} */
const attachmentPatch = {
    get urlRoute() {
        if (this.documentId) {
            if (this.documentData?.access_token) {
                return `/documents/content/${encodeURIComponent(this.documentData.access_token)}`;
            }
            return this.isImage
                ? `/web/image/${this.documentId}`
                : `/web/content/${this.documentId}`;
        }
        return super.urlRoute;
    },

    get defaultSource() {
        if (this.documentId) {
            const accessToken = this.documentData?.access_token;
            const contentUrl = accessToken
                ? `/documents/content/${encodeURIComponent(accessToken)}?download=0`
                : `/web/content/${this.documentId}?model=documents.document&download=0`;
            if (this.isPdf) {
                const encodedRoute = encodeURIComponent(contentUrl);
                return `/web/static/lib/pdfjs/web/viewer.html?file=${encodedRoute}#pagemode=none`;
            }
            if (!this.isUrlYoutube) {
                return contentUrl;
            }
        }
        return super.defaultSource;
    },

    get downloadUrl() {
        if (this.documentId && this.documentData?.access_token) {
            return `/documents/content/${encodeURIComponent(this.documentData.access_token)}?download=1`;
        }
        return super.downloadUrl;
    },

    get urlQueryParams() {
        const res = super.urlQueryParams;
        if (this.documentId) {
            res["model"] = "documents.document";
            return res;
        }
        return res;
    },

    get isDocumentEmail() {
        return this.documentId && this.mimetype === "application/documents-email";
    },

    get isHtml() {
        return this.mimetype && this.mimetype.startsWith("text/html");
    },

    get isJson() {
        return this.mimetype && this.mimetype.startsWith("application/json");
    },

    get isMimetypeTextual() {
        return (
            this.documentId &&
            this.mimetype &&
            (additionalMimeTypes.includes(this.mimetype) ||
                (textMimeTypePattern.test(this.mimetype) &&
                    !excludedMimeTypes.some((type) => this.mimetype.startsWith(type))))
        );
    },

    documentEmailContent: null,
    documentTextContent: null,

    /**
     * Fetching the attachment raw via rpc (orm_service is unavailable from here).
     * Content urls for 'application/documents-email' docs are set so as
     * browsers render strictly 'text/plain' (anti-phishing measure).
     */
    async loadDocumentEmailContent() {
        const params = {
            model: "documents.document",
            method: "read",
            args: [this.documentId, ["raw"]],
            kwargs: { context: user.context },
        };
        const result = await rpc("/web/dataset/call_kw/documents.document/read", params);
        this.documentEmailContent = result[0]["raw"];
    },
    /**
     * Fetch the content and wraps it in a styled document (with Markdown rendering for .md files)
     */
    async loadDocumentTextContent() {
        const response = await fetch(this.defaultSource);
        if (!response.ok) {
            this.documentTextContent = `<div style="font-family: system-ui, sans-serif; padding: 2rem; color: #ef4444;">Unable to load document preview (HTTP ${response.status}).</div>`;
            return;
        }
        const result = await response.text();
        const isMarkdown =
            this.mimetype === "text/markdown" ||
            (this.name && this.name.toLowerCase().endsWith(".md"));
        const styleBlock = `<style>
            :root { color-scheme: light dark; }
            body {
                margin: 0;
                padding: 28px 36px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
                font-size: 14px;
                line-height: 1.65;
                color: #0f172a;
                background: #ffffff;
            }
            @media (prefers-color-scheme: dark) {
                body { color: #e2e8f0; background: #0f172a; }
                table th { background: #1e293b !important; color: #f8fafc !important; }
                table td, table th { border-color: #334155 !important; }
                pre.md-code-block, code.md-inline-code { background: #1e293b !important; color: #e2e8f0 !important; border-color: #334155 !important; }
                blockquote { border-left-color: #3b82f6 !important; color: #94a3b8 !important; background: #1e293b40 !important; }
            }
            h1, h2, h3, h4 { margin-top: 1.4em; margin-bottom: 0.6em; font-weight: 700; line-height: 1.3; }
            h1 { font-size: 1.6rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.4rem; margin-top: 0; }
            h2 { font-size: 1.25rem; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.3rem; }
            h3 { font-size: 1.08rem; }
            p { margin: 0.65em 0; }
            ul { margin: 0.65em 0; padding-left: 1.5rem; }
            li { margin: 0.25em 0; }
            hr { border: 0; border-top: 1px solid #cbd5e1; margin: 1.5rem 0; }
            blockquote { margin: 1em 0; padding: 0.6em 1em; border-left: 4px solid #2563eb; background: #f8fafc; color: #475569; border-radius: 0 6px 6px 0; }
            pre.md-code-block, pre.plain-text {
                white-space: pre-wrap;
                word-wrap: break-word;
                font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
                font-size: 13px;
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 14px 16px;
                overflow-x: auto;
            }
            code.md-inline-code {
                font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
                font-size: 12.5px;
                background: #f1f5f9;
                padding: 2px 6px;
                border-radius: 4px;
            }
            .table-wrap { overflow-x: auto; margin: 1em 0; }
            table { border-collapse: collapse; width: 100%; font-size: 13px; }
            table th, table td { border: 1px solid #cbd5e1; padding: 8px 12px; text-align: left; }
            table th { background: #f1f5f9; font-weight: 600; }
        </style>`;
        if (isMarkdown) {
            this.documentTextContent = `<!DOCTYPE html><html><head><meta charset="utf-8"/>${styleBlock}</head><body>${renderMarkdownToHtml(result)}</body></html>`;
        } else {
            const escapedResult = result
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");
            this.documentTextContent = `<!DOCTYPE html><html><head><meta charset="utf-8"/>${styleBlock}</head><body><pre class="plain-text">${escapedResult}</pre></body></html>`;
        }
    },
};
patch(Attachment.prototype, attachmentPatch);
