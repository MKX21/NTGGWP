import io
from pathlib import Path

from django.utils import timezone
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


CERTIFICATE_FONT = 'NotoSansTC'
CERTIFICATE_FONT_PATH = (
    Path(__file__).resolve().parent / 'assets' / 'fonts' / 'NotoSansTC-Variable.ttf'
)


def _register_certificate_font():
    if CERTIFICATE_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(CERTIFICATE_FONT, str(CERTIFICATE_FONT_PATH)))


def _display_name(user):
    try:
        return user.profile.display_name
    except AttributeError:
        return user.get_full_name().strip() or user.username


def _draw_fitted_text(pdf, text, center_x, y, max_width, starting_size, color):
    font_size = starting_size
    while font_size > 14 and pdfmetrics.stringWidth(text, CERTIFICATE_FONT, font_size) > max_width:
        font_size -= 1
    pdf.setFillColor(color)
    pdf.setFont(CERTIFICATE_FONT, font_size)
    pdf.drawCentredString(center_x, y, text)


def render_certificate_pdf(certificate):
    """Return a polished, single-page completion certificate as PDF bytes."""
    _register_certificate_font()

    output = io.BytesIO()
    width, height = landscape(A4)
    pdf = canvas.Canvas(output, pagesize=(width, height))
    pdf.setTitle(f"EduFlow 結業證書 - {certificate.course.title}")
    pdf.setAuthor('EduFlow')
    pdf.setSubject('課程結業證書')

    navy = HexColor('#172554')
    purple = HexColor('#4F46E5')
    gold = HexColor('#D4A72C')
    muted = HexColor('#64748B')
    paper = HexColor('#FCFCFF')

    pdf.setFillColor(paper)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    pdf.setStrokeColor(navy)
    pdf.setLineWidth(3)
    pdf.rect(13 * mm, 13 * mm, width - 26 * mm, height - 26 * mm, fill=0, stroke=1)
    pdf.setStrokeColor(gold)
    pdf.setLineWidth(1)
    pdf.rect(18 * mm, 18 * mm, width - 36 * mm, height - 36 * mm, fill=0, stroke=1)

    center_x = width / 2
    pdf.setFillColor(purple)
    pdf.setFont('Helvetica-Bold', 18)
    pdf.drawCentredString(center_x, height - 31 * mm, 'EDUFLOW')

    pdf.setFillColor(navy)
    pdf.setFont(CERTIFICATE_FONT, 38)
    pdf.drawCentredString(center_x, height - 52 * mm, '課程結業證書')
    pdf.setFillColor(muted)
    pdf.setFont('Helvetica', 12)
    pdf.drawCentredString(center_x, height - 62 * mm, 'CERTIFICATE OF COMPLETION')

    pdf.setFillColor(muted)
    pdf.setFont(CERTIFICATE_FONT, 14)
    pdf.drawCentredString(center_x, height - 80 * mm, '茲證明')

    _draw_fitted_text(
        pdf,
        _display_name(certificate.student),
        center_x,
        height - 99 * mm,
        180 * mm,
        29,
        navy,
    )
    pdf.setStrokeColor(gold)
    pdf.setLineWidth(0.8)
    pdf.line(center_x - 68 * mm, height - 104 * mm, center_x + 68 * mm, height - 104 * mm)

    pdf.setFillColor(muted)
    pdf.setFont(CERTIFICATE_FONT, 14)
    pdf.drawCentredString(center_x, height - 119 * mm, '已完成 EduFlow 線上課程')
    _draw_fitted_text(
        pdf,
        certificate.course.title,
        center_x,
        height - 137 * mm,
        225 * mm,
        22,
        purple,
    )

    teacher_name = _display_name(certificate.course.teacher)
    issued_date = timezone.localtime(certificate.issued_at).strftime('%Y-%m-%d')
    pdf.setFillColor(navy)
    pdf.setFont(CERTIFICATE_FONT, 12)
    pdf.drawCentredString(
        center_x,
        height - 155 * mm,
        f'授課講師：{teacher_name}    核發日期：{issued_date}',
    )

    pdf.setFillColor(muted)
    pdf.setFont('Helvetica', 8)
    pdf.drawCentredString(center_x, 25 * mm, certificate.display_number)

    pdf.showPage()
    pdf.save()
    return output.getvalue()
