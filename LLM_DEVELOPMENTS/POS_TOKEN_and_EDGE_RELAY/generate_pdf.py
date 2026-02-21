from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


SOURCE = Path("LLM_DEVELOPMENTS/POS_TOKEN_and_EDGE_RELAY/POS_token_and_edge_relay.md")
TARGET = Path("LLM_DEVELOPMENTS/POS_TOKEN_and_EDGE_RELAY/POS_token_and_edge_relay.pdf")


def make_story(text: str):
    styles = getSampleStyleSheet()

    h1 = ParagraphStyle(
        "DocH1", parent=styles["Heading1"], fontSize=16, leading=20, spaceAfter=8
    )
    h2 = ParagraphStyle(
        "DocH2",
        parent=styles["Heading2"],
        fontSize=12,
        leading=16,
        spaceBefore=8,
        spaceAfter=4,
    )
    h3 = ParagraphStyle(
        "DocH3",
        parent=styles["Heading3"],
        fontSize=10,
        leading=14,
        spaceBefore=6,
        spaceAfter=3,
    )
    body = ParagraphStyle(
        "DocBody", parent=styles["BodyText"], fontSize=9, leading=12, spaceAfter=2
    )

    story = []
    for raw in text.splitlines():
        line = raw.rstrip()

        if not line:
            story.append(Spacer(1, 4))
            continue

        if line.startswith("### "):
            story.append(Paragraph(escape(line[4:]), h3))
            continue

        if line.startswith("## "):
            story.append(Paragraph(escape(line[3:]), h2))
            continue

        if line.startswith("# "):
            story.append(Paragraph(escape(line[2:]), h1))
            continue

        if line.startswith("- "):
            story.append(Paragraph(f"&bull; {escape(line[2:])}", body))
            continue

        story.append(Paragraph(escape(line), body))

    return story


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing source markdown: {SOURCE}")

    markdown = SOURCE.read_text(encoding="utf-8")

    doc = SimpleDocTemplate(
        str(TARGET),
        pagesize=A4,
        title="POS token and edge relay",
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    doc.build(make_story(markdown))

    print(f"Generated PDF: {TARGET}")


if __name__ == "__main__":
    main()
