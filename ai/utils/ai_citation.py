# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re


# Matches AI citation tokens such as [SOURCE:210] or [SOURCE:210, 211]
CITATION_REGEX = re.compile(r"""
    \[SOURCE:
        ([0-9]+
            (?:\s*,\s*[0-9]+)*
        )
    \]
""", re.VERBOSE)


def get_attachment_ids_from_text(text):
    """
    Return unique attachment ids from inline AI citation tags in the provided text.
    """
    if not text:
        return []
    sources = CITATION_REGEX.findall(text)
    attachment_ids = [int(id.strip()) for source in sources for id in source.split(',')]
    unique_attachment_ids = list(set(attachment_ids))
    return unique_attachment_ids


def apply_numeric_citations(text, attachment_data, link_attrs='target="_blank" rel="noreferrer noopener"'):
    """
    Replace inline citations with numbered, interactive evidence-grounded citation badges [1][2]...
    :param text: The input text containing citation placeholders (e.g., [SOURCE:ID1, ID2, ...])
    :param attachment_data: Map of attachment_id -> {'url', 'source_name'}
    :param link_attrs: HTML attributes for the citation link
    :return: new_content
    :rtype: str
    """
    if not text:
        return ""

    new_content = ""
    text_pieces = CITATION_REGEX.split(text)
    resolved_citations = {}
    for index, text_piece in enumerate(text_pieces):
        if index % 2 == 0:
            new_content += text_piece.rstrip(" ")
        else:
            attachment_ids = text_piece.split(',')
            for attachment_id in attachment_ids:
                attachment_id_int = int(attachment_id.strip())
                attachment_info = attachment_data.get(attachment_id_int, {})
                if not attachment_info:
                    continue
                href = attachment_info.get('url', '')
                source_name = attachment_info.get('source_name', f'Source {attachment_id_int}')
                # Clean up display name (e.g., trim long extensions or prefixes)
                display_label = source_name.rsplit('/', 1)[-1]
                if len(display_label) > 28:
                    display_label = display_label[:25] + "..."

                if attachment_id_int not in resolved_citations:
                    citation_num = len(resolved_citations) + 1
                    resolved_citations[attachment_id_int] = citation_num
                else:
                    citation_num = resolved_citations[attachment_id_int]

                # Evidence-Grounded Interactive Citation Chip (SAP Fiori / IBM Carbon Style)
                citation_html = (
                    f'<sup class="o_ai_citation_sup ms-1">'
                    f'<a href="{href}" {link_attrs} '
                    f'class="o_ai_citation_badge badge rounded-pill" '
                    f'data-attachment-id="{attachment_id_int}" '
                    f'data-source-name="{source_name}" '
                    f'title="{source_name}">'
                    f'<i class="ph ph-file-text me-1" aria-hidden="true"></i>'
                    f'[{citation_num}] {display_label}'
                    f'</a></sup>'
                )
                new_content += citation_html

    return new_content
