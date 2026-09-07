import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_sample_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=12
    )
    
    h1_style = ParagraphStyle(
        'DocH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=14,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0369a1'),
        spaceBefore=10,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )

    elements = []
    
    # Title
    elements.append(Paragraph("Renewable Energy Technologies: Solar PV, Wind & Storage", title_style))
    elements.append(Paragraph("Course Code: RET-301 | Department of Clean Energy Engineering", body_style))
    elements.append(Spacer(1, 10))

    # Read txt file
    txt_path = output_path.parent / "renewable_energy_technologies.txt"
    if txt_path.exists():
        with open(txt_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            if line_str.startswith("# "):
                elements.append(Paragraph(line_str.replace("# ", ""), h1_style))
            elif line_str.startswith("### "):
                elements.append(Paragraph(line_str.replace("### ", ""), h2_style))
            elif line_str.startswith("## "):
                elements.append(Paragraph(line_str.replace("## ", ""), h2_style))
            else:
                # Regular paragraph
                elements.append(Paragraph(line_str, body_style))
    
    doc.build(elements)
    print(f"Sample PDF successfully generated at: {output_path}")

if __name__ == "__main__":
    from backend.config import SAMPLE_DIR
    pdf_file = SAMPLE_DIR / "renewable_energy_technologies.pdf"
    generate_sample_pdf(pdf_file)
