"""
Self-contained, cross-platform PDF 1.4 document generator for MetaCheck AI Inspection Advisory Reports.
Creates structured, printable advisory dossiers with professional typography, headers, grids, and disclaimers.
"""
import io
from datetime import datetime
from typing import Any, Dict, List, Optional


class PDFDocument:
    """Lightweight pure-Python PDF 1.4 vector document builder."""

    def __init__(self, page_width: float = 595.28, page_height: float = 841.89):
        # A4 dimensions in points (72 points = 1 inch)
        self.width = page_width
        self.height = page_height
        self.pages: List[str] = []
        self.current_stream: List[str] = []
        self.current_y = self.height - 50

    def new_page(self):
        if self.current_stream:
            self.pages.append("\n".join(self.current_stream))
            self.current_stream = []
        self.current_y = self.height - 50

    def add_line(self, x1: float, y1: float, x2: float, y2: float, line_width: float = 0.5, gray: float = 0.7):
        self.current_stream.append(f"{gray:.2f} G")
        self.current_stream.append(f"{line_width:.2f} w")
        self.current_stream.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def add_rect(self, x: float, y: float, w: float, h: float, fill_rgb: Optional[tuple] = None, stroke_rgb: Optional[tuple] = None):
        cmd = ""
        if fill_rgb:
            cmd += f"{fill_rgb[0]:.2f} {fill_rgb[1]:.2f} {fill_rgb[2]:.2f} rg "
        if stroke_rgb:
            cmd += f"{stroke_rgb[0]:.2f} {stroke_rgb[1]:.2f} {stroke_rgb[2]:.2f} RG 0.5 w "
        cmd += f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re "
        if fill_rgb and stroke_rgb:
            cmd += "B"
        elif fill_rgb:
            cmd += "f"
        elif stroke_rgb:
            cmd += "S"
        self.current_stream.append(cmd)

    def add_text(
        self,
        x: float,
        y: float,
        text: str,
        size: float = 10,
        font: str = "F1",
        rgb: tuple = (0.1, 0.1, 0.1),
    ):
        # Escape parenthesis and backslashes in PDF literal strings
        escaped = (
            str(text)
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        self.current_stream.append(
            f"BT /{font} {size:.2f} Tf {rgb[0]:.2f} {rgb[1]:.2f} {rgb[2]:.2f} rg {x:.2f} {y:.2f} Td ({escaped}) Tj ET"
        )

    def build_pdf_bytes(self) -> bytes:
        if self.current_stream or not self.pages:
            self.pages.append("\n".join(self.current_stream))

        out = io.BytesIO()
        out.write(b"%PDF-1.4\n")

        objects = []
        # Obj 1: Catalog
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        # Obj 2: Pages list (filled after adding pages)
        # Obj 3: Standard Font Helvetica
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        # Obj 4: Standard Font Helvetica-Bold
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

        page_refs = []
        page_objs = []

        # Create page objects & stream objects
        base_obj_idx = 5
        for p_idx, p_stream in enumerate(self.pages):
            stream_bytes = p_stream.encode("latin1", errors="replace")
            content_obj_idx = base_obj_idx + (p_idx * 2) + 1
            page_obj_idx = base_obj_idx + (p_idx * 2)

            page_dict = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width:.2f} {self.height:.2f}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
                f"/Contents {content_obj_idx} 0 R >>"
            ).encode("latin1")

            stream_obj = (
                f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin1")
                + stream_bytes
                + b"\nendstream"
            )

            page_objs.append((page_obj_idx, page_dict))
            page_objs.append((content_obj_idx, stream_obj))
            page_refs.append(f"{page_obj_idx} 0 R")

        # Now assemble pages dictionary
        pages_dict = (
            f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(self.pages)} >>"
        ).encode("latin1")

        all_objects = [
            (1, objects[0]),
            (2, pages_dict),
            (3, objects[1]),
            (4, objects[2]),
        ] + page_objs

        # Write all objects and track offsets for xref table
        xref_offsets = [0]
        for obj_id, obj_data in sorted(all_objects, key=lambda x: x[0]):
            offset = out.tell()
            xref_offsets.append(offset)
            out.write(f"{obj_id} 0 obj\n".encode("latin1"))
            out.write(obj_data)
            out.write(b"\nendobj\n")

        # Write xref table
        xref_start = out.tell()
        out.write(f"xref\n0 {len(xref_offsets)}\n".encode("latin1"))
        out.write(b"0000000000 65535 f \n")
        for offset in xref_offsets[1:]:
            out.write(f"{offset:010d} 00000 n \n".encode("latin1"))

        # Write trailer
        trailer = (
            f"trailer\n<< /Size {len(xref_offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("latin1")
        out.write(trailer)

        return out.getvalue()


class InspectionReportPDFBuilder:
    """Builds official-style Legal Metrology Inspection Advisory Reports in PDF format."""

    def generate_advisory_report(
        self,
        inspection_data: Dict[str, Any],
        checks_data: List[Dict[str, Any]],
        violations_data: List[Dict[str, Any]],
        declarations_data: List[Dict[str, Any]],
        history_data: List[Dict[str, Any]],
    ) -> bytes:
        doc = PDFDocument()
        margin = 40
        page_width = doc.width
        content_width = page_width - (2 * margin)

        # 1. Header Banner
        doc.add_rect(margin, doc.current_y - 25, content_width, 40, fill_rgb=(0.04, 0.11, 0.22))
        doc.add_text(margin + 12, doc.current_y - 3, "METACHECK AI  |  LEGAL METROLOGY DIVISION", size=13, font="F2", rgb=(1.0, 1.0, 1.0))
        doc.add_text(margin + 12, doc.current_y - 18, "AI-Assisted Legal Metrology Inspection Report (Advisory)", size=8, font="F1", rgb=(0.7, 0.85, 1.0))
        doc.current_y -= 45

        # Sub-header info bar
        doc.add_rect(margin, doc.current_y - 16, content_width, 20, fill_rgb=(0.94, 0.96, 0.98), stroke_rgb=(0.8, 0.85, 0.9))
        gen_time = datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")
        doc.add_text(margin + 8, doc.current_y - 11, f"Report Generated: {gen_time}", size=8, font="F1", rgb=(0.3, 0.35, 0.4))
        doc.add_text(page_width - margin - 180, doc.current_y - 11, "Classification: ADVISORY SCREENING DOSSIER", size=7.5, font="F2", rgb=(0.1, 0.4, 0.7))
        doc.current_y -= 28

        # Section 1: Inspection & Commodity Summary
        doc.add_text(margin, doc.current_y, "1. INSPECTION & COMMODITY SUMMARY", size=10, font="F2", rgb=(0.05, 0.15, 0.3))
        doc.add_line(margin, doc.current_y - 3, page_width - margin, doc.current_y - 3, gray=0.7)
        doc.current_y -= 15

        insp_id = str(inspection_data.get("id", "N/A"))
        status_val = str(inspection_data.get("status", "N/A"))
        overall_res = str(inspection_data.get("overall_result_placeholder", "PENDING"))
        prod_name = str(inspection_data.get("product_name", "Packaged Commodity"))
        brand_name = str(inspection_data.get("brand", "N/A"))
        category = str(inspection_data.get("category", "General"))
        insp_date = str(inspection_data.get("inspection_date", ""))[:19]

        summary_rows = [
            ("Inspection ID:", insp_id, "Product:", prod_name[:32]),
            ("Lifecycle Status:", status_val, "Brand / Category:", f"{brand_name} ({category})"),
            ("Overall Assessment:", overall_res, "Inspection Date:", insp_date),
        ]

        for r in summary_rows:
            doc.add_text(margin + 5, doc.current_y, r[0], size=8.5, font="F2", rgb=(0.2, 0.2, 0.2))
            doc.add_text(margin + 90, doc.current_y, r[1], size=8.5, font="F1", rgb=(0.1, 0.1, 0.1))
            doc.add_text(margin + 240, doc.current_y, r[2], size=8.5, font="F2", rgb=(0.2, 0.2, 0.2))
            doc.add_text(margin + 330, doc.current_y, r[3], size=8.5, font="F1", rgb=(0.1, 0.1, 0.1))
            doc.current_y -= 13

        doc.current_y -= 10

        # Section 2: Extracted Declarations
        doc.add_text(margin, doc.current_y, "2. EXTRACTED PACKAGED COMMODITY DECLARATIONS", size=10, font="F2", rgb=(0.05, 0.15, 0.3))
        doc.add_line(margin, doc.current_y - 3, page_width - margin, doc.current_y - 3, gray=0.7)
        doc.current_y -= 14

        # Table Header
        doc.add_rect(margin, doc.current_y - 12, content_width, 16, fill_rgb=(0.92, 0.94, 0.97))
        doc.add_text(margin + 5, doc.current_y - 8, "Declaration Type", size=8, font="F2", rgb=(0.1, 0.2, 0.3))
        doc.add_text(margin + 150, doc.current_y - 8, "Normalized Statutory Value", size=8, font="F2", rgb=(0.1, 0.2, 0.3))
        doc.add_text(margin + 400, doc.current_y - 8, "Confidence", size=8, font="F2", rgb=(0.1, 0.2, 0.3))
        doc.current_y -= 18

        if not declarations_data:
            doc.add_text(margin + 10, doc.current_y, "No structured declarations extracted.", size=8, font="F1", rgb=(0.5, 0.5, 0.5))
            doc.current_y -= 14
        else:
            for d in declarations_data[:6]:
                d_type = str(d.get("declaration_type", ""))
                d_val = str(d.get("normalized_value") or d.get("raw_value") or "N/A")[:50]
                d_conf = f"{float(d.get('confidence', 0.85)) * 100:.1f}%"

                doc.add_text(margin + 5, doc.current_y, d_type, size=8, font="F1", rgb=(0.15, 0.15, 0.15))
                doc.add_text(margin + 150, doc.current_y, d_val, size=8, font="F1", rgb=(0.05, 0.05, 0.05))
                doc.add_text(margin + 400, doc.current_y, d_conf, size=8, font="F1", rgb=(0.2, 0.4, 0.2))
                doc.current_y -= 12

        doc.current_y -= 10

        # Section 3: Statutory Rule Compliance Findings
        doc.add_text(margin, doc.current_y, "3. LEGAL METROLOGY STATUTORY RULE EVALUATION", size=10, font="F2", rgb=(0.05, 0.15, 0.3))
        doc.add_line(margin, doc.current_y - 3, page_width - margin, doc.current_y - 3, gray=0.7)
        doc.current_y -= 14

        doc.add_rect(margin, doc.current_y - 12, content_width, 16, fill_rgb=(0.92, 0.94, 0.97))
        doc.add_text(margin + 5, doc.current_y - 8, "Rule Code", size=8, font="F2", rgb=(0.1, 0.2, 0.3))
        doc.add_text(margin + 120, doc.current_y - 8, "Legal Reference", size=8, font="F2", rgb=(0.1, 0.2, 0.3))
        doc.add_text(margin + 260, doc.current_y - 8, "Result", size=8, font="F2", rgb=(0.1, 0.2, 0.3))
        doc.add_text(margin + 330, doc.current_y - 8, "Finding / Advisory Explanation", size=8, font="F2", rgb=(0.1, 0.2, 0.3))
        doc.current_y -= 18

        for c in checks_data[:7]:
            r_code = str(c.get("rule_code", "RULE"))
            l_ref = str(c.get("legal_reference", "PCR 2011"))[:28]
            c_status = str(c.get("status", "PASS"))
            c_exp = str(c.get("explanation", ""))[:42]

            stat_rgb = (0.1, 0.5, 0.2) if c_status == "PASS" else ((0.8, 0.1, 0.1) if c_status == "FAIL" else (0.8, 0.5, 0.0))

            doc.add_text(margin + 5, doc.current_y, r_code, size=7.5, font="F1", rgb=(0.15, 0.15, 0.15))
            doc.add_text(margin + 120, doc.current_y, l_ref, size=7.5, font="F1", rgb=(0.2, 0.2, 0.2))
            doc.add_text(margin + 260, doc.current_y, c_status, size=7.5, font="F2", rgb=stat_rgb)
            doc.add_text(margin + 330, doc.current_y, c_exp, size=7.5, font="F1", rgb=(0.1, 0.1, 0.1))
            doc.current_y -= 12

        doc.current_y -= 10

        # Section 4: Potential Non-Compliances & Officer Review Actions
        doc.add_text(margin, doc.current_y, "4. POTENTIAL NON-COMPLIANCES & OFFICER REVIEW", size=10, font="F2", rgb=(0.05, 0.15, 0.3))
        doc.add_line(margin, doc.current_y - 3, page_width - margin, doc.current_y - 3, gray=0.7)
        doc.current_y -= 14

        if not violations_data:
            doc.add_text(margin + 5, doc.current_y, "No non-compliances flagged during automated screening.", size=8, font="F1", rgb=(0.1, 0.5, 0.2))
            doc.current_y -= 14
        else:
            for v in violations_data[:4]:
                v_code = str(v.get("violation_code", "VIOL"))
                v_sev = str(v.get("severity", "MAJOR"))
                v_stat = str(v.get("status", "FLAGGED_FOR_REVIEW"))
                v_desc = str(v.get("description", ""))[:70]
                v_comm = str(v.get("officer_comment") or "Pending officer comment")[:65]

                doc.add_text(margin + 5, doc.current_y, f"{v_code} [{v_sev}] — Status: {v_stat}", size=8, font="F2", rgb=(0.7, 0.1, 0.1))
                doc.current_y -= 10
                doc.add_text(margin + 15, doc.current_y, f"Finding: {v_desc}", size=7.5, font="F1", rgb=(0.15, 0.15, 0.15))
                doc.current_y -= 9
                doc.add_text(margin + 15, doc.current_y, f"Officer Rationale: {v_comm}", size=7.5, font="F1", rgb=(0.3, 0.3, 0.6))
                doc.current_y -= 12

        # Section 5: Statutory Disclaimer Box
        doc.current_y = max(doc.current_y - 10, 80)
        doc.add_rect(margin, doc.current_y - 50, content_width, 55, fill_rgb=(0.98, 0.98, 0.95), stroke_rgb=(0.85, 0.8, 0.6))
        doc.add_text(margin + 8, doc.current_y - 10, "Advisory / Screening Document — Not an Official Government Enforcement Order", size=8, font="F2", rgb=(0.7, 0.2, 0.0))
        doc.add_text(
            margin + 8,
            doc.current_y - 22,
            "This document is generated as an automated AI-assisted screening report under MetaCheck AI. All findings represent preliminary",
            size=7.2,
            font="F1",
            rgb=(0.3, 0.3, 0.3),
        )
        doc.add_text(
            margin + 8,
            doc.current_y - 32,
            "advisory observations. Final legal compliance determinations and statutory compounding notices rest exclusively with authorized",
            size=7.2,
            font="F1",
            rgb=(0.3, 0.3, 0.3),
        )
        doc.add_text(
            margin + 8,
            doc.current_y - 42,
            "Legal Metrology Officers pursuant to The Legal Metrology Act, 2009 and Legal Metrology (Packaged Commodities) Rules, 2011.",
            size=7.2,
            font="F1",
            rgb=(0.3, 0.3, 0.3),
        )

        return doc.build_pdf_bytes()


pdf_builder = InspectionReportPDFBuilder()
