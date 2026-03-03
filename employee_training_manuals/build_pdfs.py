from pathlib import Path
import re
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
PDF_DIR = ROOT / "pdf"


IMAGE_RE = re.compile(r"^!\[(?P<alt>.*?)\]\((?P<path>.*?)\)\s*$")
NUMBERED_RE = re.compile(r"^(?P<num>\d+)\.\s+(?P<text>.+)$")


def make_styles():
    styles = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle(
            "DocH1",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            spaceBefore=0,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "DocH2",
            parent=styles["Heading2"],
            fontSize=12,
            leading=16,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "h3": ParagraphStyle(
            "DocH3",
            parent=styles["Heading3"],
            fontSize=10,
            leading=14,
            spaceBefore=6,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "DocBody",
            parent=styles["BodyText"],
            fontSize=9.5,
            leading=13,
            spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "DocBullet",
            parent=styles["BodyText"],
            fontSize=9.5,
            leading=13,
            leftIndent=10,
            bulletIndent=0,
            spaceAfter=2,
        ),
        "caption": ParagraphStyle(
            "DocCaption",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
            textColor="#555555",
            alignment=1,
            spaceBefore=2,
            spaceAfter=6,
        ),
    }


def _build_image(path: Path, max_width: float, max_height: float):
    if not path.exists():
        raise FileNotFoundError(f"Missing image: {path}")
    reader = ImageReader(str(path))
    width_px, height_px = reader.getSize()
    scale = min(max_width / width_px, max_height / height_px, 1.0)
    img = Image(str(path), width=width_px * scale, height=height_px * scale)
    img.hAlign = "CENTER"
    return img


def make_story(md_path: Path, doc, styles):
    story = []
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    for raw in lines:
        line = raw.rstrip()
        if not line:
            story.append(Spacer(1, 4))
            continue

        image_match = IMAGE_RE.match(line)
        if image_match:
            image_path = (md_path.parent / image_match.group("path")).resolve()
            alt = image_match.group("alt").strip()
            story.append(Spacer(1, 4))
            story.append(_build_image(image_path, max_width=doc.width, max_height=125 * mm))
            if alt:
                story.append(Paragraph(escape(alt), styles["caption"]))
            else:
                story.append(Spacer(1, 3))
            continue

        if line.startswith("### "):
            story.append(Paragraph(escape(line[4:]), styles["h3"]))
            continue
        if line.startswith("## "):
            story.append(Paragraph(escape(line[3:]), styles["h2"]))
            continue
        if line.startswith("# "):
            story.append(Paragraph(escape(line[2:]), styles["h1"]))
            continue

        numbered = NUMBERED_RE.match(line)
        if numbered:
            num = escape(numbered.group("num"))
            txt = escape(numbered.group("text"))
            story.append(Paragraph(f"{num}. {txt}", styles["bullet"]))
            continue

        if line.startswith("- "):
            story.append(Paragraph(f"&bull; {escape(line[2:])}", styles["bullet"]))
            continue

        story.append(Paragraph(escape(line), styles["body"]))
    return story


def _draw_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(A4[0] - 14 * mm, 8 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def title_from_markdown(md_path: Path):
    for line in md_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return md_path.stem


def build_pdf(md_path: Path):
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    target = PDF_DIR / f"{md_path.stem}.pdf"
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        title=title_from_markdown(md_path),
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    story = make_story(md_path, doc, styles)
    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    print(f"Generated PDF: {target}")


def main():
    if not SRC_DIR.exists():
        raise FileNotFoundError(f"Missing source directory: {SRC_DIR}")
    markdown_files = sorted(SRC_DIR.glob("*.md"))
    if not markdown_files:
        raise FileNotFoundError(f"No markdown files found in: {SRC_DIR}")
    for md_file in markdown_files:
        build_pdf(md_file)


if __name__ == "__main__":
    main()

