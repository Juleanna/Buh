"""
Генерація PDF-документів для обліку основних засобів.

Типові форми Мінфіну України:
- ОЗ-1: Акт приймання-передачі (внутрішнього переміщення) основних засобів
- ОЗ-3: Акт списання основних засобів
- ОЗ-4: Акт списання автотранспортних засобів
- ОЗ-6: Інвентарна картка обліку основних засобів
- Інв-1: Інвентаризаційний опис основних засобів (Наказ МФУ 17.06.2015 №572)

Додатково:
- Відомість нарахування амортизації (Наказ МФУ 13.09.2016 №818)
- Оборотна відомість (Наказ МФУ 5.02.2021 №101)
- Журнал проводок
"""
import io
import os
from datetime import datetime, date
from decimal import Decimal

from django.http import HttpResponse
from django.db.models import Sum, Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from apps.assets.models import (
    Asset, AssetGroup, AssetReceipt, AssetDisposal,
    DepreciationRecord, Inventory, InventoryItem,
    AccountEntry, AssetRevaluation, AssetImprovement,
    Organization,
)
from apps.documents.excel_utils import (
    create_workbook, write_header_row, write_data_row, write_total_row,
    write_info_row, write_section_header, auto_width, workbook_to_response,
    write_form_header, write_form_header_landscape, write_approval_block,
    write_text_row, write_signatures_block, write_commission_signatures,
    write_merged_header, write_column_numbers_row,
)


# ---------------------------------------------------------------------------
# Font registration: try to find a Cyrillic-capable font on the system
# ---------------------------------------------------------------------------
FONT_REGISTERED = False
for font_path in [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    'C:/Windows/Fonts/arial.ttf',
    'C:/Windows/Fonts/times.ttf',
]:
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('UkrFont', font_path))
            FONT_REGISTERED = True
            break
        except Exception:
            pass

FONT_NAME = 'UkrFont' if FONT_REGISTERED else 'Helvetica'

APPROVAL_ORDER = 'наказом Мiнфiну України\nвiд 13.09.2016 №818'


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_styles():
    """Build ParagraphStyle set using the registered Cyrillic font."""
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        'UkrTitle',
        parent=styles['Title'],
        fontName=FONT_NAME,
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    ))
    styles.add(ParagraphStyle(
        'UkrSubtitle',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        'UkrNormal',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=9,
        leading=12,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        'UkrRight',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=9,
        leading=12,
        alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        'UkrCenter',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        'UkrSmall',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=7,
        leading=9,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        'UkrSmallCenter',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=7,
        leading=9,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        'UkrBold',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=9,
        leading=12,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        'UkrFormStamp',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=7,
        leading=9,
        alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        'UkrFormTitle',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        spaceAfter=3 * mm,
        spaceBefore=2 * mm,
    ))
    styles.add(ParagraphStyle(
        'UkrSignature',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=8,
        leading=11,
        alignment=TA_LEFT,
    ))
    return styles


def _fmt(value, fmt='{:,.2f}'):
    """Format a Decimal / numeric value for display."""
    if value is None:
        return '-'
    return fmt.format(value)


def _header_table_style():
    """Standard TableStyle for the header info block."""
    return TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.93, 0.93, 0.93)),
        ('LEFTPADDING', (0, 0), (-1, -1), 3 * mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 2 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2 * mm),
    ])


def _data_table_style(header_rows=1):
    """Standard TableStyle for data grids with a coloured header row."""
    style_commands = [
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, header_rows - 1),
         colors.Color(0.85, 0.85, 0.85)),
        ('LEFTPADDING', (0, 0), (-1, -1), 2 * mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 1.5 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5 * mm),
        ('ALIGN', (0, 0), (-1, header_rows - 1), 'CENTER'),
    ]
    return TableStyle(style_commands)


def _build_pdf(buffer, elements, pagesize=A4, margins=None):
    """Convenience wrapper around SimpleDocTemplate.build()."""
    if margins is None:
        margins = dict(
            topMargin=15 * mm, bottomMargin=15 * mm,
            leftMargin=12 * mm, rightMargin=12 * mm,
        )
    doc = SimpleDocTemplate(buffer, pagesize=pagesize, **margins)
    doc.build(elements)
    buffer.seek(0)
    return buffer


def _make_response(buffer, filename):
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _p(text, style):
    """Shortcut to create a Paragraph (wraps long text inside table cells)."""
    return Paragraph(str(text), style)


def _location_display(obj):
    """Safe display of a location FK (asset.location or inventory.location)."""
    if obj and obj.location:
        return obj.location.name
    return '\u2014'


def _responsible_person_display(asset):
    """Safe display of asset.responsible_person FK."""
    if asset.responsible_person:
        return asset.responsible_person.full_name
    return '\u2014'


# ---------------------------------------------------------------------------
# Official form helpers
# ---------------------------------------------------------------------------

def _form_header_block(org, form_number, form_name, styles,
                       approval_text=None):
    """
    Build the standard official Minfin form header.

    Returns a list of flowables:
    - Two-column table: left = org info, right = form stamp + EDRPOU
    - Centered form title
    """
    elements = []

    # Left column: org info
    org_name = org.name if org else '________________________________'
    org_edrpou = org.edrpou if org else '________'
    org_address = org.address if org and org.address else ''

    left_lines = f'{org_name}'
    if org_address:
        left_lines += f'<br/>{org_address}'

    # Right column: form stamp
    if approval_text is None:
        approval_text = APPROVAL_ORDER

    right_lines = (
        f'Типова форма №{form_number}<br/>'
        f'ЗАТВЕРДЖЕНО<br/>'
        f'{approval_text.replace(chr(10), "<br/>")}<br/>'
        f'<br/>Код ЄДРПОУ  {org_edrpou}'
    )

    header_data = [[
        _p(left_lines, styles['UkrNormal']),
        _p(right_lines, styles['UkrFormStamp']),
    ]]
    header_table = Table(header_data, colWidths=[95 * mm, 85 * mm])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4 * mm))

    # Centered title
    elements.append(Paragraph(form_name, styles['UkrFormTitle']))

    return elements


def _form_header_block_landscape(org, form_name, styles, approval_text=None):
    """
    Build a landscape-oriented official Minfin form header (no form number).

    Returns a list of flowables.
    """
    elements = []

    org_name = org.name if org else '________________________________'
    org_edrpou = org.edrpou if org else '________'

    if approval_text is None:
        approval_text = APPROVAL_ORDER

    right_lines = (
        f'ЗАТВЕРДЖЕНО<br/>'
        f'{approval_text.replace(chr(10), "<br/>")}<br/>'
    )

    header_data = [[
        _p(org_name + f'<br/>Код ЄДРПОУ  {org_edrpou}', styles['UkrNormal']),
        _p(right_lines, styles['UkrFormStamp']),
    ]]
    page_w = landscape(A4)[0] - 24 * mm  # total usable width
    header_table = Table(header_data, colWidths=[page_w * 0.55, page_w * 0.45])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph(form_name, styles['UkrFormTitle']))

    return elements


def _approval_block(org, styles):
    """
    Build the "ЗАТВЕРДЖУЮ" approval block.

    Returns a list of flowables.
    """
    director = org.director if org and org.director else '________________'

    approval_data = [[
        '',
        _p(
            'ЗАТВЕРДЖУЮ<br/>'
            f'Керiвник ____________ {director}<br/>'
            '<br/>'
            '"___" ____________ 20__ р.',
            styles['UkrRight'],
        ),
    ]]
    approval_table = Table(approval_data, colWidths=[95 * mm, 85 * mm])
    approval_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    return [approval_table, Spacer(1, 3 * mm)]


def _commission_signatures_block(head_user, members_qs, styles):
    """
    Build individual signature lines for commission members.

    Returns a list of flowables with named signature lines.
    """
    elements = []
    elements.append(Spacer(1, 10 * mm))

    sig_data = []

    # Commission head
    head_name = head_user.get_full_name() if head_user else '________________'
    sig_data.append([
        _p('Голова комiсiї:', styles['UkrSignature']),
        '____________',
        _p(head_name, styles['UkrSignature']),
    ])

    # Commission members
    if members_qs:
        member_list = list(members_qs)
        for i, member in enumerate(member_list):
            label = 'Члени комiсiї:' if i == 0 else ''
            sig_data.append([
                _p(label, styles['UkrSignature']),
                '____________',
                _p(member.get_full_name(), styles['UkrSignature']),
            ])
    else:
        # Blank lines for commission members
        for i in range(3):
            label = 'Члени комiсiї:' if i == 0 else ''
            sig_data.append([
                _p(label, styles['UkrSignature']),
                '____________',
                '________________',
            ])

    sig_table = Table(sig_data, colWidths=[40 * mm, 35 * mm, 80 * mm])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2 * mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 3 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1 * mm),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
    ]))
    elements.append(sig_table)

    # Signature labels
    label_data = [['', _p('(пiдпис)', styles['UkrSmall']),
                   _p('(прiзвище, iнiцiали)', styles['UkrSmall'])]]
    label_table = Table(label_data, colWidths=[40 * mm, 35 * mm, 80 * mm])
    label_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('ALIGN', (1, 0), (2, 0), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(label_table)

    return elements


def _official_signatures(roles_and_names, styles):
    """
    Build signature lines for specific roles.

    roles_and_names: list of (role_label, name_or_blank) tuples
    Returns a list of flowables.
    """
    elements = []
    elements.append(Spacer(1, 12 * mm))

    sig_data = []
    for role, name in roles_and_names:
        sig_data.append([
            _p(f'{role}:', styles['UkrSignature']),
            '____________',
            _p(name or '________________', styles['UkrSignature']),
        ])

    sig_table = Table(sig_data, colWidths=[50 * mm, 35 * mm, 70 * mm])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2 * mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 4 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1 * mm),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
    ]))
    elements.append(sig_table)

    label_data = [['', _p('(пiдпис)', styles['UkrSmall']),
                   _p('(прiзвище, iнiцiали)', styles['UkrSmall'])]]
    label_table = Table(label_data, colWidths=[50 * mm, 35 * mm, 70 * mm])
    label_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('ALIGN', (1, 0), (2, 0), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(label_table)

    return elements


def _get_org_from_request_or_default(request):
    """Try to determine the organization from request user or return first."""
    try:
        return Organization.objects.first()
    except Exception:
        return None


# ============================================================================
# 1. AssetCardPDFView  --  ОЗ-6 Інвентарна картка обліку ОЗ
# ============================================================================

class AssetCardPDFView(APIView):
    """
    ОЗ-6 -- Iнвентарна картка облiку основних засобiв.

    GET /documents/asset/<pk>/card/
    """
    permission_classes = [IsAuthenticated]

    def _build_xlsx(self, asset):
        org = asset.organization
        num_cols = 6
        wb, ws = create_workbook('Картка ОЗ')
        row = 1

        # -- Official header --
        row = write_form_header(
            ws, row, org, 'ОЗ-6',
            'IНВЕНТАРНА КАРТКА облiку основних засобiв',
            num_cols, approval_text=APPROVAL_ORDER,
        )

        # -- Card info line --
        write_info_row(ws, row, 'Картка №', asset.inventory_number, label_col=1, value_col=2)
        write_info_row(ws, row, 'Дата вiдкриття', asset.commissioning_date.strftime('%d.%m.%Y'), label_col=3, value_col=4)
        write_info_row(ws, row, 'Дата закриття', asset.disposal_date.strftime('%d.%m.%Y') if asset.disposal_date else '\u2014', label_col=5, value_col=6)
        row += 2

        # -- Main asset data --
        write_info_row(ws, row, 'Назва об\'єкта:', asset.name); row += 1
        write_info_row(ws, row, 'Iнвентарний номер:', asset.inventory_number); row += 1
        write_info_row(ws, row, 'Група ОЗ:', str(asset.group)); row += 1
        write_info_row(ws, row, 'Рахунок облiку:', asset.group.account_number); row += 1
        write_info_row(ws, row, 'Рахунок зносу:', asset.group.depreciation_account); row += 1
        write_info_row(ws, row, 'Статус:', asset.get_status_display()); row += 1
        write_info_row(ws, row, 'Дата введення в експлуатацiю:', asset.commissioning_date.strftime('%d.%m.%Y')); row += 1
        write_info_row(ws, row, 'Дата початку амортизацiї:', asset.depreciation_start_date.strftime('%d.%m.%Y')); row += 1
        write_info_row(ws, row, 'МВО:', _responsible_person_display(asset)); row += 1
        write_info_row(ws, row, 'Мiсцезнаходження:', _location_display(asset)); row += 1
        if asset.description:
            write_info_row(ws, row, 'Опис / характеристики:', asset.description); row += 1
        row += 1

        # -- Cost section --
        write_section_header(ws, row, 'Вартiснi характеристики', num_cols); row += 1
        write_info_row(ws, row, 'Первiсна вартiсть, грн:', float(asset.initial_cost) if asset.initial_cost else 0); row += 1
        write_info_row(ws, row, 'Лiквiдацiйна вартiсть, грн:', float(asset.residual_value) if asset.residual_value else 0); row += 1
        write_info_row(ws, row, 'Залишкова (балансова) вартiсть, грн:', float(asset.current_book_value) if asset.current_book_value else 0); row += 1
        write_info_row(ws, row, 'Накопичений знос, грн:', float(asset.accumulated_depreciation) if asset.accumulated_depreciation else 0); row += 1
        row += 1

        # -- Depreciation params --
        write_section_header(ws, row, 'Параметри амортизацiї', num_cols); row += 1
        write_info_row(ws, row, 'Метод амортизацiї:', asset.get_depreciation_method_display()); row += 1
        write_info_row(ws, row, 'Строк корисного використання (мiс.):', str(asset.useful_life_months)); row += 1
        if asset.total_production_capacity:
            write_info_row(ws, row, 'Загальний обсяг продукцiї (од.):', float(asset.total_production_capacity) if asset.total_production_capacity else 0); row += 1
        row += 1

        # -- Depreciation history (last 12) --
        records = DepreciationRecord.objects.filter(asset=asset).order_by(
            '-period_year', '-period_month',
        )[:12]

        if records.exists():
            write_section_header(ws, row, 'Iсторiя нарахування амортизацiї (останнi 12 записiв)', 5); row += 1
            headers = ['Перiод', 'Метод', 'Вартiсть до, грн', 'Сума амортизацiї, грн', 'Вартiсть пiсля, грн']
            write_header_row(ws, row, headers); row += 1
            money = {3, 4, 5}
            for rec in reversed(list(records)):
                write_data_row(ws, row, [
                    f'{rec.period_month:02d}.{rec.period_year}',
                    rec.get_depreciation_method_display()[:20],
                    float(rec.book_value_before) if rec.book_value_before else 0,
                    float(rec.amount) if rec.amount else 0,
                    float(rec.book_value_after) if rec.book_value_after else 0,
                ], money_cols=money)
                row += 1
            row += 1

        # -- Improvements (last 5) --
        improvements = AssetImprovement.objects.filter(
            asset=asset,
        ).order_by('-date')[:5]

        if improvements.exists():
            write_section_header(ws, row, 'Полiпшення / ремонти', 5); row += 1
            headers = ['Дата', 'Тип', 'Документ', 'Сума, грн', 'Збiльшує вартiсть']
            write_header_row(ws, row, headers); row += 1
            for imp in improvements:
                write_data_row(ws, row, [
                    imp.date.strftime('%d.%m.%Y'),
                    imp.get_improvement_type_display()[:25],
                    imp.document_number,
                    float(imp.amount) if imp.amount else 0,
                    'Так' if imp.increases_value else 'Нi',
                ], money_cols={4})
                row += 1
            row += 1

        # -- Revaluations (last 5) --
        revaluations = AssetRevaluation.objects.filter(
            asset=asset,
        ).order_by('-date')[:5]

        if revaluations.exists():
            write_section_header(ws, row, 'Переоцiнки', 6); row += 1
            headers = ['Дата', 'Тип', 'Документ', 'Вартiсть до, грн', 'Справедлива вартiсть, грн', 'Сума переоцiнки, грн']
            write_header_row(ws, row, headers); row += 1
            money = {4, 5, 6}
            for rev in revaluations:
                write_data_row(ws, row, [
                    rev.date.strftime('%d.%m.%Y'),
                    rev.get_revaluation_type_display(),
                    rev.document_number,
                    float(rev.old_book_value) if rev.old_book_value else 0,
                    float(rev.fair_value) if rev.fair_value else 0,
                    float(rev.revaluation_amount) if rev.revaluation_amount else 0,
                ], money_cols=money)
                row += 1
            row += 1

        # -- Accountant signature --
        accountant = org.accountant if org and org.accountant else '________________'
        row = write_signatures_block(ws, row, [
            ('Картку заповнив', accountant),
        ], num_cols=num_cols)

        auto_width(ws, num_cols)
        return workbook_to_response(wb, f'asset_card_{asset.inventory_number}.xlsx')

    def get(self, request, pk):
        asset = Asset.objects.select_related(
            'group', 'responsible_person', 'organization', 'location',
        ).get(pk=pk)

        fmt = request.query_params.get('export')
        if fmt == 'xlsx':
            return self._build_xlsx(asset)

        org = asset.organization
        styles = _get_styles()
        elements = []

        # -- Official header --
        elements.extend(_form_header_block(
            org, 'ОЗ-6',
            'IНВЕНТАРНА КАРТКА облiку основних засобiв',
            styles,
        ))
        elements.append(Spacer(1, 2 * mm))

        # -- Card info line --
        card_info = [
            [
                'Картка №', asset.inventory_number,
                'Дата вiдкриття',
                asset.commissioning_date.strftime('%d.%m.%Y'),
                'Дата закриття',
                asset.disposal_date.strftime('%d.%m.%Y') if asset.disposal_date else '\u2014',
            ],
        ]
        card_table = Table(card_info, colWidths=[
            22 * mm, 30 * mm, 28 * mm, 25 * mm, 28 * mm, 25 * mm,
        ])
        card_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, 0), colors.Color(0.93, 0.93, 0.93)),
            ('BACKGROUND', (2, 0), (2, 0), colors.Color(0.93, 0.93, 0.93)),
            ('BACKGROUND', (4, 0), (4, 0), colors.Color(0.93, 0.93, 0.93)),
            ('LEFTPADDING', (0, 0), (-1, -1), 2 * mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2 * mm),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5 * mm),
        ]))
        elements.append(card_table)
        elements.append(Spacer(1, 3 * mm))

        # -- Main asset data --
        info_rows = [
            ['Назва об\'єкта:', _p(asset.name, styles['UkrNormal'])],
            ['Iнвентарний номер:', asset.inventory_number],
            ['Група ОЗ:', str(asset.group)],
            ['Рахунок облiку:', asset.group.account_number],
            ['Рахунок зносу:', asset.group.depreciation_account],
            ['Статус:', asset.get_status_display()],
            ['Дата введення в експлуатацiю:',
             asset.commissioning_date.strftime('%d.%m.%Y')],
            ['Дата початку амортизацiї:',
             asset.depreciation_start_date.strftime('%d.%m.%Y')],
            ['МВО:', _responsible_person_display(asset)],
            ['Мiсцезнаходження:', _location_display(asset)],
        ]
        if asset.description:
            info_rows.append(['Опис / характеристики:',
                              _p(asset.description, styles['UkrNormal'])])

        info_table = Table(info_rows, colWidths=[65 * mm, 105 * mm])
        info_table.setStyle(_header_table_style())
        elements.append(info_table)
        elements.append(Spacer(1, 4 * mm))

        # -- Cost information --
        elements.append(Paragraph(
            'Вартiснi характеристики', styles['UkrSubtitle'],
        ))
        cost_rows = [
            ['Первiсна вартiсть, грн:', _fmt(asset.initial_cost)],
            ['Лiквiдацiйна вартiсть, грн:', _fmt(asset.residual_value)],
            ['Залишкова (балансова) вартiсть, грн:',
             _fmt(asset.current_book_value)],
            ['Накопичений знос, грн:',
             _fmt(asset.accumulated_depreciation)],
        ]
        cost_table = Table(cost_rows, colWidths=[65 * mm, 105 * mm])
        cost_table.setStyle(_header_table_style())
        elements.append(cost_table)
        elements.append(Spacer(1, 4 * mm))

        # -- Depreciation parameters --
        elements.append(Paragraph(
            'Параметри амортизацiї', styles['UkrSubtitle'],
        ))
        depr_rows = [
            ['Метод амортизацiї:', asset.get_depreciation_method_display()],
            ['Строк корисного використання (мiс.):',
             str(asset.useful_life_months)],
        ]
        if asset.total_production_capacity:
            depr_rows.append([
                'Загальний обсяг продукцiї (од.):',
                _fmt(asset.total_production_capacity),
            ])
        depr_table = Table(depr_rows, colWidths=[65 * mm, 105 * mm])
        depr_table.setStyle(_header_table_style())
        elements.append(depr_table)
        elements.append(Spacer(1, 4 * mm))

        # -- Depreciation history (last 12 records) --
        records = DepreciationRecord.objects.filter(asset=asset).order_by(
            '-period_year', '-period_month',
        )[:12]

        if records.exists():
            elements.append(Paragraph(
                'Iсторiя нарахування амортизацiї (останнi 12 записiв)',
                styles['UkrSubtitle'],
            ))
            elements.append(Spacer(1, 2 * mm))

            depr_header = [
                _p('Перiод', styles['UkrSmall']),
                _p('Метод', styles['UkrSmall']),
                _p('Вартiсть до, грн', styles['UkrSmall']),
                _p('Сума амортизацiї, грн', styles['UkrSmall']),
                _p('Вартiсть пiсля, грн', styles['UkrSmall']),
            ]
            depr_data = [depr_header]
            for rec in reversed(list(records)):
                depr_data.append([
                    f'{rec.period_month:02d}.{rec.period_year}',
                    rec.get_depreciation_method_display()[:20],
                    _fmt(rec.book_value_before),
                    _fmt(rec.amount),
                    _fmt(rec.book_value_after),
                ])

            depr_col_widths = [22 * mm, 40 * mm, 32 * mm, 38 * mm, 38 * mm]
            dt = Table(depr_data, colWidths=depr_col_widths)
            ts = _data_table_style()
            ts.add('ALIGN', (2, 1), (-1, -1), 'RIGHT')
            dt.setStyle(ts)
            elements.append(dt)
            elements.append(Spacer(1, 4 * mm))

        # -- Recent improvements --
        improvements = AssetImprovement.objects.filter(
            asset=asset,
        ).order_by('-date')[:5]

        if improvements.exists():
            elements.append(Paragraph(
                'Полiпшення / ремонти', styles['UkrSubtitle'],
            ))
            elements.append(Spacer(1, 2 * mm))

            imp_header = [
                _p('Дата', styles['UkrSmall']),
                _p('Тип', styles['UkrSmall']),
                _p('Документ', styles['UkrSmall']),
                _p('Сума, грн', styles['UkrSmall']),
                _p('Збiльшує вартiсть', styles['UkrSmall']),
            ]
            imp_data = [imp_header]
            for imp in improvements:
                imp_data.append([
                    imp.date.strftime('%d.%m.%Y'),
                    imp.get_improvement_type_display()[:25],
                    imp.document_number,
                    _fmt(imp.amount),
                    'Так' if imp.increases_value else 'Нi',
                ])
            imp_col_widths = [22 * mm, 40 * mm, 35 * mm, 35 * mm, 30 * mm]
            it = Table(imp_data, colWidths=imp_col_widths)
            ts = _data_table_style()
            ts.add('ALIGN', (3, 1), (3, -1), 'RIGHT')
            it.setStyle(ts)
            elements.append(it)
            elements.append(Spacer(1, 4 * mm))

        # -- Recent revaluations --
        revaluations = AssetRevaluation.objects.filter(
            asset=asset,
        ).order_by('-date')[:5]

        if revaluations.exists():
            elements.append(Paragraph(
                'Переоцiнки', styles['UkrSubtitle'],
            ))
            elements.append(Spacer(1, 2 * mm))

            rev_header = [
                _p('Дата', styles['UkrSmall']),
                _p('Тип', styles['UkrSmall']),
                _p('Документ', styles['UkrSmall']),
                _p('Вартiсть до, грн', styles['UkrSmall']),
                _p('Справедлива вартiсть, грн', styles['UkrSmall']),
                _p('Сума переоцiнки, грн', styles['UkrSmall']),
            ]
            rev_data = [rev_header]
            for rev in revaluations:
                rev_data.append([
                    rev.date.strftime('%d.%m.%Y'),
                    rev.get_revaluation_type_display(),
                    rev.document_number,
                    _fmt(rev.old_book_value),
                    _fmt(rev.fair_value),
                    _fmt(rev.revaluation_amount),
                ])
            rev_col_widths = [20 * mm, 22 * mm, 25 * mm, 30 * mm, 35 * mm, 30 * mm]
            rt = Table(rev_data, colWidths=rev_col_widths)
            ts = _data_table_style()
            ts.add('ALIGN', (3, 1), (-1, -1), 'RIGHT')
            rt.setStyle(ts)
            elements.append(rt)

        # -- Accountant signature --
        accountant = org.accountant if org and org.accountant else '________________'
        elements.extend(_official_signatures([
            ('Картку заповнив', accountant),
        ], styles))

        # -- Build PDF --
        buf = io.BytesIO()
        _build_pdf(buf, elements)
        return _make_response(
            buf,
            f'asset_card_{asset.inventory_number}.pdf',
        )


# ============================================================================
# 2. DepreciationReportPDFView  --  Відомість нарахування амортизації
#    Наказ Міністерства фінансів України 13.09.2016 № 818
# ============================================================================

class DepreciationReportPDFView(APIView):
    """
    Вiдомiсть нарахування амортизацiї за мiсяць.

    Форма згiдно з Наказом Мiнiстерства фiнансiв України 13.09.2016 №818.

    GET /documents/depreciation-report/?year=2025&month=3
    """
    permission_classes = [IsAuthenticated]

    def _build_xlsx(self, records, year, month):
        wb, ws = create_workbook(f'Амортизація {month:02d}.{year}')
        row = 1

        headers = [
            'Субрахунок', 'Інв.номер', 'Назва',
            'Вартість що амортизується', 'Річна сума',
            'К-ть місяців', 'Знос на початок',
            'Нарахована амортизація', 'Знос на кінець',
            'Субрахунок витрат', 'Примітка',
        ]
        write_header_row(ws, row, headers); row += 1
        money = {4, 5, 7, 8, 9}

        total_depreciable = Decimal('0.00')
        total_annual = Decimal('0.00')
        total_wear_start = Decimal('0.00')
        total_amount = Decimal('0.00')
        total_wear_end = Decimal('0.00')

        for rec in records:
            asset = rec.asset
            sub_account = asset.group.account_number if asset.group else ''
            depreciable_value = asset.initial_cost - asset.residual_value
            if asset.depreciation_rate:
                annual_depreciation = (
                    asset.initial_cost * asset.depreciation_rate / Decimal('100')
                )
            else:
                annual_depreciation = rec.amount * 12
            months_used = 1
            wear_start = asset.initial_cost - rec.book_value_before
            period_amount = rec.amount
            wear_end = wear_start + period_amount
            expense_account = '92'

            write_data_row(ws, row, [
                sub_account,
                asset.inventory_number,
                asset.name[:50],
                float(depreciable_value),
                float(annual_depreciation),
                months_used,
                float(wear_start),
                float(period_amount),
                float(wear_end),
                expense_account,
                '',
            ], money_cols=money)
            row += 1

            total_depreciable += depreciable_value
            total_annual += annual_depreciation
            total_wear_start += wear_start
            total_amount += period_amount
            total_wear_end += wear_end

        write_total_row(ws, row, [
            '', '', 'РАЗОМ:',
            float(total_depreciable),
            float(total_annual),
            '',
            float(total_wear_start),
            float(total_amount),
            float(total_wear_end),
            '', '',
        ], money_cols=money)

        auto_width(ws, 11)
        return workbook_to_response(wb, f'depreciation_{year}_{month:02d}.xlsx')

    def get(self, request):
        year = int(request.query_params.get('year', datetime.now().year))
        month = int(request.query_params.get('month', datetime.now().month))

        records = DepreciationRecord.objects.filter(
            period_year=year, period_month=month,
        ).select_related(
            'asset', 'asset__group', 'asset__responsible_person',
            'asset__location', 'asset__organization',
        ).order_by('asset__group__account_number', 'asset__inventory_number')

        fmt = request.query_params.get('export')
        if fmt == 'xlsx':
            return self._build_xlsx(records, year, month)

        org = _get_org_from_request_or_default(request)
        # Try to get org from the first record
        if records.exists():
            first_asset = records.first().asset
            if first_asset.organization:
                org = first_asset.organization

        styles = _get_styles()
        elements = []

        # -- Official header (landscape) --
        approval_text = (
            'Наказ Мiнiстерства фiнансiв України\n'
            '13.09.2016 № 818'
        )
        elements.extend(_form_header_block_landscape(
            org,
            'Розрахунок амортизацiї основних засобiв<br/>'
            '(крiм iнших необоротних матерiальних активiв)',
            styles,
            approval_text=approval_text,
        ))

        elements.append(Paragraph(
            f'за {year} р.',
            styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 4 * mm))

        # -- Data table (11 columns per Наказ №818) --
        # Two-row header with merged cells
        header_row = [
            _p('Субрахунок', styles['UkrSmallCenter']),
            _p('Iнвентарний<br/>номер', styles['UkrSmallCenter']),
            _p('Назва<br/>об\'єкта', styles['UkrSmallCenter']),
            _p('Вартiсть,<br/>яка<br/>амортизується', styles['UkrSmallCenter']),
            _p('Рiчна сума<br/>амортизацiї', styles['UkrSmallCenter']),
            _p('Кiлькiсть<br/>мiсяцiв<br/>корисного<br/>використання<br/>(експлуатацiї)<br/>у перiодi', styles['UkrSmallCenter']),
            _p('Сума зносу<br/>на початок<br/>перiоду', styles['UkrSmallCenter']),
            _p('Сума<br/>нарахованої<br/>амортизацiї<br/>за перiод', styles['UkrSmallCenter']),
            _p('Сума зносу<br/>на кiнець<br/>перiоду<br/>(гр. 7 + гр. 8)', styles['UkrSmallCenter']),
            _p('Субрахунок<br/>витрат', styles['UkrSmallCenter']),
            _p('Примiтка', styles['UkrSmallCenter']),
        ]

        # Column numbers row
        col_num_row = [
            _p(str(i), styles['UkrSmallCenter']) for i in range(1, 12)
        ]

        data = [header_row, col_num_row]

        total_depreciable = Decimal('0.00')
        total_annual = Decimal('0.00')
        total_wear_start = Decimal('0.00')
        total_amount = Decimal('0.00')
        total_wear_end = Decimal('0.00')

        for rec in records:
            asset = rec.asset

            # Column 1: Субрахунок
            sub_account = asset.group.account_number if asset.group else ''

            # Column 4: Вартість, яка амортизується
            depreciable_value = asset.initial_cost - asset.residual_value

            # Column 5: Річна сума амортизації
            if asset.depreciation_rate:
                annual_depreciation = (
                    asset.initial_cost * asset.depreciation_rate / Decimal('100')
                )
            else:
                annual_depreciation = rec.amount * 12

            # Column 6: К-ть місяців корисного використання у періоді
            months_used = 1

            # Column 7: Сума зносу на початок періоду
            wear_start = rec.book_value_before - rec.book_value_after
            # accumulated_depreciation - amount gives the wear at start
            # book_value_before = initial_cost - accumulated_at_start
            # so accumulated_at_start = initial_cost - book_value_before
            wear_start = asset.initial_cost - rec.book_value_before
            # This is accumulated depreciation before this record

            # Column 8: Сума нарахованої амортизації за період
            period_amount = rec.amount

            # Column 9: Сума зносу на кінець періоду (гр.7 + гр.8)
            wear_end = wear_start + period_amount

            # Column 10: Субрахунок витрат
            expense_account = '92'

            data.append([
                sub_account,
                asset.inventory_number,
                _p(asset.name[:50], styles['UkrSmall']),
                _fmt(depreciable_value),
                _fmt(annual_depreciation),
                str(months_used),
                _fmt(wear_start),
                _fmt(period_amount),
                _fmt(wear_end),
                expense_account,
                '',
            ])

            total_depreciable += depreciable_value
            total_annual += annual_depreciation
            total_wear_start += wear_start
            total_amount += period_amount
            total_wear_end += wear_end

        # Totals row
        data.append([
            '', '',
            _p('РАЗОМ:', styles['UkrSmall']),
            _fmt(total_depreciable),
            _fmt(total_annual),
            '',
            _fmt(total_wear_start),
            _fmt(total_amount),
            _fmt(total_wear_end),
            '', '',
        ])

        page_w = landscape(A4)[0] - 24 * mm
        col_widths = [
            page_w * 0.06,   # 1 - Субрахунок
            page_w * 0.09,   # 2 - Інв. номер
            page_w * 0.17,   # 3 - Назва
            page_w * 0.10,   # 4 - Вартість амортизується
            page_w * 0.10,   # 5 - Річна сума
            page_w * 0.06,   # 6 - К-ть місяців
            page_w * 0.10,   # 7 - Знос на початок
            page_w * 0.10,   # 8 - Сума амортизації
            page_w * 0.10,   # 9 - Знос на кінець
            page_w * 0.06,   # 10 - Субрахунок витрат
            page_w * 0.06,   # 11 - Примітка
        ]

        table = Table(data, colWidths=col_widths)
        ts = _data_table_style(header_rows=2)
        ts.add('ALIGN', (3, 2), (8, -1), 'RIGHT')
        ts.add('ALIGN', (5, 2), (5, -1), 'CENTER')
        ts.add('ALIGN', (9, 2), (9, -1), 'CENTER')
        ts.add('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.93, 0.93, 0.93))
        ts.add('FONTSIZE', (0, -1), (-1, -1), 8)
        table.setStyle(ts)
        elements.append(table)

        # -- Footer summary --
        elements.append(Spacer(1, 5 * mm))
        elements.append(Paragraph(
            f'Всього записiв: {records.count()}',
            styles['UkrNormal'],
        ))
        elements.append(Paragraph(
            f'Загальна сума амортизацiї: {_fmt(total_amount)} грн',
            styles['UkrNormal'],
        ))

        # -- Signatures --
        elements.extend(_official_signatures([
            ('Головний бухгалтер',
             org.accountant if org and org.accountant else ''),
            ('Виконавець', ''),
        ], styles))

        # -- Build PDF --
        buf = io.BytesIO()
        _build_pdf(buf, elements, pagesize=landscape(A4))
        return _make_response(
            buf,
            f'depreciation_report_{year}_{month:02d}.pdf',
        )


# ============================================================================
# 3. InventoryReportPDFView  --  Інвентаризаційний опис ОЗ
#    Наказ Міністерства фінансів України 17.06.2015 № 572
# ============================================================================

class InventoryReportPDFView(APIView):
    """
    Iнвентаризацiйний опис необоротних активiв.

    Форма згiдно з Наказом Мiнiстерства фiнансiв України 17.06.2015 №572.

    GET /documents/inventory/<pk>/report/
    """
    permission_classes = [IsAuthenticated]

    def _build_xlsx(self, inventory, items):
        wb, ws = create_workbook('Інвентаризація')
        row = 1

        # -- Info rows --
        write_info_row(ws, row, 'Номер:', inventory.number); row += 1
        write_info_row(ws, row, 'Дата:', inventory.date.strftime('%d.%m.%Y') if inventory.date else ''); row += 1
        write_info_row(ws, row, 'Наказ:', f'№{inventory.order_number} від {inventory.order_date.strftime("%d.%m.%Y") if inventory.order_date else ""}'); row += 1
        write_info_row(ws, row, 'Місце:', inventory.location.name if inventory.location else ''); row += 1
        write_info_row(ws, row, 'Статус:', inventory.get_status_display() if hasattr(inventory, 'get_status_display') else ''); row += 1
        row += 1

        headers = [
            '№ з/п', 'Найменування', 'Рік випуску', 'Інв.номер',
            'Завод.номер', 'Паспорт', 'Од.виміру', 'Факт к-ть',
            'Факт вартість', 'Вибуття', 'Бухоблік к-ть',
            'Бухоблік вартість', 'Знос', 'Балансова вартість',
            'Строк використання',
        ]
        write_header_row(ws, row, headers); row += 1
        money = {9, 12, 13, 14}

        total_fact_qty = 0
        total_fact_value = Decimal('0.00')
        total_book_qty = 0
        total_book_value = Decimal('0.00')
        total_depreciation = Decimal('0.00')
        total_balance = Decimal('0.00')

        for i, item in enumerate(items, 1):
            asset = item.asset
            year_or_date = ''
            if asset.manufacture_year:
                year_or_date = str(asset.manufacture_year)
            elif asset.commissioning_date:
                year_or_date = str(asset.commissioning_date.year)

            fact_qty = 1 if item.is_found else 0
            fact_value = asset.initial_cost if item.is_found else Decimal('0.00')

            disposal_note = ''
            if asset.status == Asset.Status.DISPOSED:
                disposal_note = 'вибув'

            write_data_row(ws, row, [
                i,
                asset.name[:50],
                year_or_date,
                asset.inventory_number,
                asset.factory_number or '',
                asset.passport_number or '',
                asset.unit_of_measure or 'шт.',
                fact_qty,
                float(fact_value),
                disposal_note,
                1,
                float(asset.initial_cost),
                float(asset.accumulated_depreciation),
                float(asset.current_book_value),
                asset.useful_life_months,
            ], money_cols=money)
            row += 1

            total_fact_qty += fact_qty
            total_fact_value += fact_value
            total_book_qty += 1
            total_book_value += asset.initial_cost
            total_depreciation += asset.accumulated_depreciation
            total_balance += asset.current_book_value

        # "Разом на сторінці" row
        write_total_row(ws, row, [
            '', 'Разом на сторінці', '', '', '', '', '',
            total_fact_qty,
            float(total_fact_value),
            '',
            total_book_qty,
            float(total_book_value),
            float(total_depreciation),
            float(total_balance),
            '',
        ], money_cols=money)
        row += 1

        # "РАЗОМ" row
        write_total_row(ws, row, [
            '', 'РАЗОМ', '', '', '', '', '',
            total_fact_qty,
            float(total_fact_value),
            '',
            total_book_qty,
            float(total_book_value),
            float(total_depreciation),
            float(total_balance),
            '',
        ], money_cols=money)

        auto_width(ws, 15)
        return workbook_to_response(wb, f'inventory_{inventory.number}.xlsx')

    def get(self, request, pk):
        inventory = Inventory.objects.prefetch_related(
            'items__asset__group', 'commission_members',
        ).select_related('commission_head', 'location').get(pk=pk)

        items = inventory.items.select_related(
            'asset', 'asset__group', 'asset__organization',
            'asset__responsible_person', 'asset__location',
        ).order_by('asset__inventory_number')

        fmt = request.query_params.get('export')
        if fmt == 'xlsx':
            return self._build_xlsx(inventory, items)

        # Detect organization from first item
        org = None
        first_item = items.first()
        if first_item and first_item.asset.organization:
            org = first_item.asset.organization

        styles = _get_styles()
        elements = []

        page_w = landscape(A4)[0] - 24 * mm

        # -- Top-right approval stamp --
        org_name = org.name if org else '________________________________'
        approval_data = [[
            _p(org_name, styles['UkrNormal']),
            _p(
                'ЗАТВЕРДЖЕНО<br/>'
                'Наказ Мiнiстерства фiнансiв України<br/>'
                '17.06.2015  № 572',
                styles['UkrFormStamp'],
            ),
        ]]
        approval_table = Table(approval_data, colWidths=[page_w * 0.55, page_w * 0.45])
        approval_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(approval_table)
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(
            '(установа)', styles['UkrSmallCenter'],
        ))
        elements.append(Spacer(1, 4 * mm))

        # -- Title and subtitle --
        elements.append(Paragraph(
            'Iнвентаризацiйний опис необоротних активiв',
            styles['UkrFormTitle'],
        ))
        elements.append(Paragraph(
            '(основнi засоби, нематерiальнi активи, iншi необоротнi '
            'матерiальнi активи, капiтальнi iнвестицiї)',
            styles['UkrSmallCenter'],
        ))
        elements.append(Spacer(1, 2 * mm))

        # -- Date line --
        inv_date = inventory.date.strftime('%d.%m.%Y') if inventory.date else ''
        elements.append(Paragraph(
            f'\u00ab____\u00bb ______________ {inventory.date.year if inventory.date else "____"} р.',
            styles['UkrCenter'],
        ))
        elements.append(Spacer(1, 3 * mm))

        # -- Descriptive text block --
        inv_location = (
            inventory.location.name if inventory.location else '______________________'
        )
        elements.append(Paragraph(
            f'На пiдставi розпорядчого документа '
            f'№{inventory.order_number} вiд {inventory.order_date.strftime("%d.%m.%Y") if inventory.order_date else "________"}  '
            f'виконано знiмання фактичних залишкiв',
            styles['UkrNormal'],
        ))
        elements.append(Paragraph(
            'основних засобiв, нематерiальних активiв, iнших необоротних '
            'матерiальних активiв, капiтальнi iнвестицiї (необхiдне пiдкреслити), '
            'якi облiковуються на субрахунку(ах)',
            styles['UkrNormal'],
        ))
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(
            '_____________________________________________________________',
            styles['UkrNormal'],
        ))
        elements.append(Paragraph(
            '(номер та назва)',
            styles['UkrSmallCenter'],
        ))
        elements.append(Paragraph(
            f'та зберiгаються {inv_location}',
            styles['UkrNormal'],
        ))
        elements.append(Paragraph(
            '(мiсцезнаходження)',
            styles['UkrSmallCenter'],
        ))
        elements.append(Paragraph(
            f'станом на \u00ab{inventory.date.strftime("%d")}\u00bb '
            f'{inventory.date.strftime("%m")} '
            f'{inventory.date.year} р.',
            styles['UkrNormal'],
        ))
        elements.append(Spacer(1, 4 * mm))

        # -- Розписка --
        elements.append(Paragraph(
            'Розписка',
            styles['UkrCenter'],
        ))
        elements.append(Spacer(1, 1 * mm))
        elements.append(Paragraph(
            'До початку проведення iнвентаризацiї всi видатковi та прибутковi '
            'документи на необоротнi активи зданi в бухгалтерську службу i всi '
            'необоротнi активи, що надiйшли на мою вiдповiдальнiсть, '
            'оприбуткованi, а тi, що вибули, списанi.',
            styles['UkrNormal'],
        ))
        elements.append(Spacer(1, 3 * mm))

        # -- МВО signature in Розписка --
        mvo_rozp = [[
            _p('Матерiально вiдповiдальна особа:', styles['UkrSignature']),
            '____________',
            '____________',
            '________________',
        ]]
        mvo_rozp_table = Table(mvo_rozp, colWidths=[55 * mm, 35 * mm, 30 * mm, 50 * mm])
        mvo_rozp_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
        ]))
        elements.append(mvo_rozp_table)
        mvo_label = [[
            '',
            _p('(посада)', styles['UkrSmallCenter']),
            _p('(пiдпис)', styles['UkrSmallCenter']),
            _p('(iнiцiали, прiзвище)', styles['UkrSmallCenter']),
        ]]
        mvo_label_table = Table(mvo_label, colWidths=[55 * mm, 35 * mm, 30 * mm, 50 * mm])
        mvo_label_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(mvo_label_table)
        elements.append(Spacer(1, 2 * mm))

        # -- Інвентаризація dates --
        elements.append(Paragraph(
            f'Iнвентаризацiя:    розпочата \u00ab______\u00bb _________ '
            f'{inventory.date.year if inventory.date else "____"} р.',
            styles['UkrNormal'],
        ))
        elements.append(Paragraph(
            f'                        закiнчена \u00ab____\u00bb ____________ '
            f'{inventory.date.year if inventory.date else "____"} р.',
            styles['UkrNormal'],
        ))
        elements.append(Spacer(1, 3 * mm))

        # -- Pre-table text --
        elements.append(Paragraph(
            '_______________________________________',
            styles['UkrNormal'],
        ))
        elements.append(Paragraph(
            'При iнвентаризацiї встановлено таке:',
            styles['UkrNormal'],
        ))
        elements.append(Spacer(1, 2 * mm))

        # -- Items table (16 columns per Наказ №572) --
        # Multi-level header: 5 rows (header_row0..header_row3 + col_numbers)
        #
        # Row 0 (top-level groups):
        #   col 0: № з/п
        #   col 1: Найменування...
        #   col 2: Рiк випуску...
        #   cols 3-5: Номер (SPAN)
        #   col 6: Один. вимiр.
        #   cols 7-8: Фактична наявнiсть (SPAN)
        #   col 9: Вiдмiтка про вибуття
        #   cols 10-14: За даними бухгалтерського облiку (SPAN)
        #   col 15: (empty)
        #
        # Row 1 (sub-headers for "Номер"):
        #   cols 3: iнвентарний/номенклатурний
        #   cols 4: заводський
        #   cols 5: паспорта
        #
        # Row 2 (sub-headers for "Фактична наявнiсть" and "За даними бухоблiку"):
        #   col 7: кiлькiсть
        #   col 8: первiсна (переоцiнена)вартiсть
        #   col 10: кiлькiсть
        #   col 11: первiсна (переоцiнена) вартiсть
        #   col 12: сума зносу (накопиченої амортизацiї)
        #   col 13: балансова вартiсть
        #   col 14: строк корисного використання
        #
        # Row 3: column numbers 1-16

        s = styles['UkrSmallCenter']

        header_row0 = [
            _p('№<br/>з/п', s),
            _p('Найменування,<br/>стисла характеристика<br/>та призначення<br/>об\'єкта', s),
            _p('Рiк випуску<br/>(будiвництва)<br/>чи дата придбання<br/>(введення в<br/>експлуатацiю)<br/>та виготовлювач', s),
            _p('Номер', s), '', '',
            _p('Один.<br/>вимiр.', s),
            _p('Фактична наявнiсть', s), '',
            _p('Вiдмiтка<br/>про<br/>вибуття', s),
            _p('За даними бухгалтерського облiку', s), '', '', '', '',
            '',  # col 16 - empty
        ]

        header_row1 = [
            '', '', '',
            _p('iнвентарний/<br/>номенклатурний', s),
            _p('заводський', s),
            _p('паспорта', s),
            '', '', '',
            '', '', '', '', '', '',
            '',
        ]

        header_row2 = [
            '', '', '',
            '', '', '',
            '',
            _p('кiлькiсть', s),
            _p('первiсна<br/>(переоцiнена)<br/>вартiсть', s),
            '',
            _p('кiлькiсть', s),
            _p('первiсна<br/>(переоцiнена)<br/>вартiсть', s),
            _p('сума зносу<br/>(накопиченої<br/>амортизацiї)', s),
            _p('балансова<br/>вартiсть', s),
            _p('строк<br/>корисного<br/>використання', s),
            '',
        ]

        col_num_row = [
            _p(str(i), styles['UkrSmallCenter']) for i in range(1, 17)
        ]

        data = [header_row0, header_row1, header_row2, col_num_row]

        total_fact_qty = 0
        total_fact_value = Decimal('0.00')
        total_book_qty = 0
        total_book_value = Decimal('0.00')
        total_depreciation = Decimal('0.00')
        total_balance = Decimal('0.00')
        found_count = 0
        shortage_count = 0

        for i, item in enumerate(items, 1):
            asset = item.asset

            # Column 3: Year of manufacture or acquisition date
            year_or_date = ''
            if asset.manufacture_year:
                year_or_date = str(asset.manufacture_year)
            elif asset.commissioning_date:
                year_or_date = str(asset.commissioning_date.year)

            # Column 8: Factual quantity (1 if found, 0 if not)
            fact_qty = 1 if item.is_found else 0

            # Column 9: Factual initial cost (only if found)
            fact_value = asset.initial_cost if item.is_found else Decimal('0.00')

            # Column 10: Disposal note
            disposal_note = ''
            if asset.status == Asset.Status.DISPOSED:
                disposal_note = 'вибув'

            data.append([
                str(i),
                _p(asset.name[:50], styles['UkrSmall']),
                year_or_date,
                asset.inventory_number,
                asset.factory_number or '',
                asset.passport_number or '',
                asset.unit_of_measure or 'шт.',
                str(fact_qty),
                _fmt(fact_value),
                disposal_note,
                '1',
                _fmt(asset.initial_cost),
                _fmt(asset.accumulated_depreciation),
                _fmt(asset.current_book_value),
                str(asset.useful_life_months),
                '',  # col 16
            ])

            total_fact_qty += fact_qty
            total_fact_value += fact_value
            total_book_qty += 1
            total_book_value += asset.initial_cost
            total_depreciation += asset.accumulated_depreciation
            total_balance += asset.current_book_value
            if item.is_found:
                found_count += 1
            else:
                shortage_count += 1

        total_items = items.count()

        # "Разом на сторiнцi" row
        data.append([
            '', _p('Разом на сторiнцi', styles['UkrSmall']),
            '', '', '', '', '',
            str(total_fact_qty),
            _fmt(total_fact_value),
            '',
            str(total_book_qty),
            _fmt(total_book_value),
            _fmt(total_depreciation),
            _fmt(total_balance),
            '', '',
        ])

        # "РАЗОМ" row
        data.append([
            '', _p('РАЗОМ', styles['UkrSmall']),
            '', '', '', '', '',
            str(total_fact_qty),
            _fmt(total_fact_value),
            '',
            str(total_book_qty),
            _fmt(total_book_value),
            _fmt(total_depreciation),
            _fmt(total_balance),
            '', '',
        ])

        col_widths = [
            page_w * 0.028,  # 1  - № з/п
            page_w * 0.130,  # 2  - Найменування
            page_w * 0.060,  # 3  - Рік випуску
            page_w * 0.065,  # 4  - Інв. номер
            page_w * 0.050,  # 5  - Завод. номер
            page_w * 0.050,  # 6  - Паспорт
            page_w * 0.035,  # 7  - Од. виміру
            page_w * 0.040,  # 8  - Факт к-ть
            page_w * 0.078,  # 9  - Факт вартість
            page_w * 0.045,  # 10 - Вибуття
            page_w * 0.040,  # 11 - Бухоблік к-ть
            page_w * 0.078,  # 12 - Бухоблік вартість
            page_w * 0.078,  # 13 - Знос
            page_w * 0.078,  # 14 - Балансова вартість
            page_w * 0.055,  # 15 - Строк корисного використання
            page_w * 0.030,  # 16 - (empty)
        ]

        header_rows = 4  # rows 0-3 are headers
        table = Table(data, colWidths=col_widths)
        ts = _data_table_style(header_rows=header_rows)

        # SPAN merges for multi-level header
        # Row 0-2 vertical spans for single-column headers
        ts.add('SPAN', (0, 0), (0, 2))    # № з/п spans rows 0-2
        ts.add('SPAN', (1, 0), (1, 2))    # Найменування spans rows 0-2
        ts.add('SPAN', (2, 0), (2, 2))    # Рiк випуску spans rows 0-2
        ts.add('SPAN', (6, 0), (6, 2))    # Один. вимiр. spans rows 0-2
        ts.add('SPAN', (9, 0), (9, 2))    # Вiдмiтка про вибуття spans rows 0-2
        ts.add('SPAN', (15, 0), (15, 2))  # col 16 empty spans rows 0-2

        # Row 0 group headers (horizontal + vertical spans)
        ts.add('SPAN', (3, 0), (5, 0))    # "Номер" spans cols 3-5 in row 0
        ts.add('SPAN', (7, 0), (8, 1))    # "Фактична наявнiсть" spans cols 7-8, rows 0-1
        ts.add('SPAN', (10, 0), (14, 1))  # "За даними бухоблiку" spans cols 10-14, rows 0-1

        # Row 1-2 sub-headers for "Номер"
        ts.add('SPAN', (3, 1), (3, 2))    # iнвентарний spans rows 1-2
        ts.add('SPAN', (4, 1), (4, 2))    # заводський spans rows 1-2
        ts.add('SPAN', (5, 1), (5, 2))    # паспорта spans rows 1-2

        # Data alignment
        ts.add('ALIGN', (0, header_rows), (0, -1), 'CENTER')
        ts.add('ALIGN', (7, header_rows), (8, -1), 'RIGHT')
        ts.add('ALIGN', (10, header_rows), (14, -1), 'RIGHT')

        # Summary rows background
        ts.add('BACKGROUND', (0, -2), (-1, -1), colors.Color(0.93, 0.93, 0.93))

        table.setStyle(ts)
        elements.append(table)

        # -- Page summary text --
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(
            f'Число порядкових номерiв на сторiнцi: {total_items} '
            f'(з 1 по {total_items})&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
            f'Загальна кiлькiсть у натуральних вимiрах фактично на сторiнцi: {total_fact_qty}',
            styles['UkrNormal'],
        ))
        elements.append(Paragraph(
            f'Загальна кiлькiсть у натуральних вимiрах за даними бухоблiку на сторiнцi: {total_book_qty}',
            styles['UkrNormal'],
        ))
        elements.append(Spacer(1, 4 * mm))

        # -- "Разом за описом" summary block --
        elements.append(Paragraph(
            f'Разом за описом:    а) кiлькiсть порядкових номерiв ______ ',
            styles['UkrNormal'],
        ))
        elements.append(Paragraph(
            '(прописом)',
            styles['UkrSmallCenter'],
        ))
        elements.append(Paragraph(
            f'б) загальна кiлькiсть одиниць,  фактично - {total_fact_qty} ',
            styles['UkrNormal'],
        ))
        elements.append(Paragraph(
            '(прописом)',
            styles['UkrSmallCenter'],
        ))
        elements.append(Paragraph(
            f'в) вартiсть фактична - {_fmt(total_fact_value)}',
            styles['UkrNormal'],
        ))
        elements.append(Spacer(1, 1 * mm))
        elements.append(Paragraph(
            f'г) загальна кiлькiсть одиниць,  за даними бухгалтерського облiку - {total_book_qty}',
            styles['UkrNormal'],
        ))
        elements.append(Paragraph(
            '(прописом)',
            styles['UkrSmallCenter'],
        ))
        elements.append(Paragraph(
            f'\u0491) вартiсть за даними бухгалтерського облiку - {_fmt(total_book_value)}',
            styles['UkrNormal'],
        ))
        elements.append(Paragraph(
            '(прописом)',
            styles['UkrSmallCenter'],
        ))
        elements.append(Spacer(1, 5 * mm))

        # -- Commission signatures --
        # Голова комiсiї
        head_name = ''
        if inventory.commission_head:
            head_name = inventory.commission_head.get_full_name()

        sig_data = [[
            _p('Голова комiсiї:', styles['UkrSignature']),
            '____________',
            '____________',
            _p(head_name or '________________', styles['UkrSignature']),
        ]]
        sig_label = [[
            '',
            _p('(посада)', styles['UkrSmallCenter']),
            _p('(пiдпис)', styles['UkrSmallCenter']),
            _p('(iнiцiали, прiзвище)', styles['UkrSmallCenter']),
        ]]

        # Члени комiсiї
        members = list(inventory.commission_members.all())
        for idx in range(max(len(members), 4)):
            label = 'Члени комiсiї:' if idx == 0 else ''
            member_name = members[idx].get_full_name() if idx < len(members) else '________________'
            sig_data.append([
                _p(label, styles['UkrSignature']),
                '____________',
                '____________',
                _p(member_name, styles['UkrSignature']),
            ])
            sig_label.append([
                '',
                _p('(посада)', styles['UkrSmallCenter']),
                _p('(пiдпис)', styles['UkrSmallCenter']),
                _p('(iнiцiали, прiзвище)', styles['UkrSmallCenter']),
            ])

        sig_table = Table(sig_data, colWidths=[40 * mm, 40 * mm, 30 * mm, 60 * mm])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('ALIGN', (1, 0), (2, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 3 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1 * mm),
        ]))
        elements.append(sig_table)

        sig_label_table = Table(sig_label, colWidths=[40 * mm, 40 * mm, 30 * mm, 60 * mm])
        sig_label_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(sig_label_table)
        elements.append(Spacer(1, 5 * mm))

        # -- МВО final text --
        elements.append(Paragraph(
            'Усi цiнностi, пронумерованi в цьому iнвентаризацiйному описi '
            'з №1 до №'
            f'{total_items}'
            ', перевiренi комiсiєю в натурi в моїй присутностi '
            'та внесенi в опис, у зв\'язку з чим претензiй до '
            'iнвентаризацiйної комiсiї не маю. Цiнностi, перелiченi '
            'в описi, знаходяться на моєму вiдповiдальному зберiганнi.',
            styles['UkrNormal'],
        ))
        elements.append(Spacer(1, 3 * mm))

        # -- МВО signature --
        mvo_final = [[
            _p('Матерiально вiдповiдальна особа:', styles['UkrSignature']),
            '',
            '',
            '',
        ]]
        mvo_final_table = Table(mvo_final, colWidths=[55 * mm, 35 * mm, 30 * mm, 50 * mm])
        mvo_final_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ]))
        elements.append(mvo_final_table)

        elements.append(Paragraph(
            f'\u00ab___\u00bb _________________ '
            f'{inventory.date.year if inventory.date else "____"} р.',
            styles['UkrNormal'],
        ))
        elements.append(Spacer(1, 1 * mm))

        mvo_sig2 = [[
            '',
            _p('____________', styles['UkrSmallCenter']),
            _p('____________', styles['UkrSmallCenter']),
            _p('________________', styles['UkrSmallCenter']),
        ]]
        mvo_sig2_table = Table(mvo_sig2, colWidths=[55 * mm, 35 * mm, 30 * mm, 50 * mm])
        mvo_sig2_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 2 * mm),
        ]))
        elements.append(mvo_sig2_table)
        mvo_sig2_label = [[
            '',
            _p('(посада)', styles['UkrSmallCenter']),
            _p('(пiдпис)', styles['UkrSmallCenter']),
            _p('(iнiцiали, прiзвище)', styles['UkrSmallCenter']),
        ]]
        mvo_sig2_label_table = Table(mvo_sig2_label, colWidths=[55 * mm, 35 * mm, 30 * mm, 50 * mm])
        mvo_sig2_label_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(mvo_sig2_label_table)
        elements.append(Spacer(1, 5 * mm))

        # -- "Інформацію за даними бухобліку вніс:" --
        elements.append(Paragraph(
            'Iнформацiю за даними бухгалтерського облiку внiс:',
            styles['UkrNormal'],
        ))
        elements.append(Spacer(1, 1 * mm))
        info_sig = [[
            '____________',
            '____________',
            '________________',
        ]]
        info_sig_table = Table(info_sig, colWidths=[50 * mm, 40 * mm, 60 * mm])
        info_sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 2 * mm),
        ]))
        elements.append(info_sig_table)
        info_sig_label = [[
            _p('(посада)', styles['UkrSmallCenter']),
            _p('(пiдпис)', styles['UkrSmallCenter']),
            _p('(iнiцiали, прiзвище)', styles['UkrSmallCenter']),
        ]]
        info_sig_label_table = Table(info_sig_label, colWidths=[50 * mm, 40 * mm, 60 * mm])
        info_sig_label_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(info_sig_label_table)
        elements.append(Spacer(1, 4 * mm))

        # -- "Вказані у цьому описі дані перевірив:" --
        elements.append(Paragraph(
            'Вказанi у цьому описi данi перевiрив:',
            styles['UkrNormal'],
        ))
        elements.append(Paragraph(
            f'\u00ab____\u00bb _________________ '
            f'{inventory.date.year if inventory.date else "____"} р.',
            styles['UkrNormal'],
        ))
        elements.append(Spacer(1, 1 * mm))
        check_sig = [[
            '____________',
            '____________',
            '________________',
        ]]
        check_sig_table = Table(check_sig, colWidths=[50 * mm, 40 * mm, 60 * mm])
        check_sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 2 * mm),
        ]))
        elements.append(check_sig_table)
        check_sig_label = [[
            _p('(посада)', styles['UkrSmallCenter']),
            _p('(пiдпис)', styles['UkrSmallCenter']),
            _p('(iнiцiали, прiзвище)', styles['UkrSmallCenter']),
        ]]
        check_sig_label_table = Table(check_sig_label, colWidths=[50 * mm, 40 * mm, 60 * mm])
        check_sig_label_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(check_sig_label_table)

        # -- Build PDF --
        buf = io.BytesIO()
        _build_pdf(buf, elements, pagesize=landscape(A4))
        return _make_response(
            buf,
            f'inventory_report_{inventory.number}.pdf',
        )


# ============================================================================
# 4. AssetReceiptActPDFView  --  ОЗ-1 Акт приймання-передачі ОЗ
# ============================================================================

class AssetReceiptActPDFView(APIView):
    """
    ОЗ-1 -- Акт приймання-передачi (внутрiшнього перемiщення) основних засобiв.

    GET /documents/receipt/<pk>/act/
    """
    permission_classes = [IsAuthenticated]

    def _build_xlsx(self, receipt, asset, org):
        wb, ws = create_workbook('Акт ОЗ-1')
        row = 1

        write_info_row(ws, row, 'Акт №:', receipt.document_number); row += 1
        write_info_row(ws, row, 'Дата:', receipt.document_date.strftime('%d.%m.%Y')); row += 1
        write_info_row(ws, row, 'Тип надходження:', receipt.get_receipt_type_display()); row += 1
        write_info_row(ws, row, 'Постачальник:', receipt.supplier or '\u2014'); row += 1
        write_info_row(ws, row, 'Інв. номер:', asset.inventory_number); row += 1
        write_info_row(ws, row, 'Назва:', asset.name); row += 1
        write_info_row(ws, row, 'Група:', str(asset.group)); row += 1
        write_info_row(ws, row, 'Рахунок:', asset.group.account_number); row += 1
        write_info_row(ws, row, 'Дата введення:', asset.commissioning_date.strftime('%d.%m.%Y')); row += 1
        write_info_row(ws, row, 'Метод амортизації:', asset.get_depreciation_method_display()); row += 1
        write_info_row(ws, row, 'Строк (міс.):', asset.useful_life_months); row += 1
        write_info_row(ws, row, 'Місцезнаходження:', _location_display(asset)); row += 1
        write_info_row(ws, row, 'МВО:', _responsible_person_display(asset)); row += 1
        row += 1

        # -- Cost rows --
        write_section_header(ws, row, 'Вартість об\'єкта', 2); row += 1
        write_info_row(ws, row, 'Сума за документом:', float(receipt.amount) if receipt.amount else 0); row += 1
        write_info_row(ws, row, 'Первісна вартість:', float(asset.initial_cost) if asset.initial_cost else 0); row += 1
        write_info_row(ws, row, 'Ліквідаційна вартість:', float(asset.residual_value) if asset.residual_value else 0); row += 1

        auto_width(ws, 2)
        return workbook_to_response(wb, f'receipt_act_{receipt.document_number}.xlsx')

    def get(self, request, pk):
        receipt = AssetReceipt.objects.select_related(
            'asset', 'asset__group', 'asset__responsible_person',
            'asset__organization', 'asset__location', 'created_by',
        ).get(pk=pk)
        asset = receipt.asset
        org = asset.organization

        fmt = request.query_params.get('export')
        if fmt == 'xlsx':
            return self._build_xlsx(receipt, asset, org)

        styles = _get_styles()
        elements = []

        # -- Official header --
        elements.extend(_form_header_block(
            org, 'ОЗ-1',
            'АКТ приймання-передачi (внутрiшнього перемiщення)<br/>'
            'основних засобiв',
            styles,
        ))

        # -- Approval block --
        elements.extend(_approval_block(org, styles))

        # -- Document info --
        elements.append(Paragraph(
            f'Акт №{receipt.document_number} вiд '
            f'{receipt.document_date.strftime("%d.%m.%Y")}',
            styles['UkrCenter'],
        ))
        elements.append(Spacer(1, 4 * mm))

        # -- Section 1: Document details --
        doc_rows = [
            ['Тип надходження:', receipt.get_receipt_type_display()],
            ['Постачальник / джерело:', receipt.supplier or '\u2014'],
        ]
        doc_table = Table(doc_rows, colWidths=[55 * mm, 115 * mm])
        doc_table.setStyle(_header_table_style())
        elements.append(doc_table)
        elements.append(Spacer(1, 4 * mm))

        # -- Section 2: Asset info --
        elements.append(Paragraph(
            'Вiдомостi про об\'єкт основних засобiв',
            styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 2 * mm))

        asset_rows = [
            ['Iнвентарний номер:', asset.inventory_number],
            ['Назва:', _p(asset.name, styles['UkrNormal'])],
            ['Група ОЗ:', str(asset.group)],
            ['Рахунок облiку:', asset.group.account_number],
            ['Рахунок зносу:', asset.group.depreciation_account],
            ['Дата введення в експлуатацiю:',
             asset.commissioning_date.strftime('%d.%m.%Y')],
            ['Метод амортизацiї:',
             asset.get_depreciation_method_display()],
            ['Строк корисного використання (мiс.):',
             str(asset.useful_life_months)],
            ['Мiсцезнаходження:', _location_display(asset)],
            ['МВО:', _responsible_person_display(asset)],
        ]
        if asset.description:
            asset_rows.append(['Опис:', _p(asset.description[:200], styles['UkrNormal'])])
        asset_table = Table(asset_rows, colWidths=[55 * mm, 115 * mm])
        asset_table.setStyle(_header_table_style())
        elements.append(asset_table)
        elements.append(Spacer(1, 4 * mm))

        # -- Section 3: Cost --
        elements.append(Paragraph(
            'Вартiсть об\'єкта', styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 2 * mm))

        cost_rows = [
            ['Сума за документом, грн:', _fmt(receipt.amount)],
            ['Первiсна вартiсть, грн:', _fmt(asset.initial_cost)],
            ['Лiквiдацiйна вартiсть, грн:', _fmt(asset.residual_value)],
        ]
        cost_table = Table(cost_rows, colWidths=[55 * mm, 60 * mm])
        cost_table.setStyle(_header_table_style())
        elements.append(cost_table)

        # -- Notes --
        if receipt.notes:
            elements.append(Spacer(1, 4 * mm))
            elements.append(Paragraph(
                f'Примiтки: {receipt.notes}', styles['UkrNormal'],
            ))

        # -- Signatures --
        elements.extend(_official_signatures([
            ('Здав', ''),
            ('Прийняв', _responsible_person_display(asset)),
            ('Гол. бухгалтер', org.accountant if org and org.accountant else ''),
        ], styles))

        # -- Stamp place --
        elements.append(Spacer(1, 5 * mm))
        stamp_data = [['М.П.', '', 'М.П.']]
        stamp_table = Table(stamp_data, colWidths=[50 * mm, 55 * mm, 50 * mm])
        stamp_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(stamp_table)

        # -- Build PDF --
        buf = io.BytesIO()
        _build_pdf(buf, elements)
        return _make_response(
            buf,
            f'receipt_act_{receipt.document_number}.pdf',
        )


# ============================================================================
# 5. AssetDisposalActPDFView  --  ОЗ-3 Акт списання ОЗ
# ============================================================================

class AssetDisposalActPDFView(APIView):
    """
    ОЗ-3 -- Акт списання основних засобiв.

    GET /documents/disposal/<pk>/act/
    """
    permission_classes = [IsAuthenticated]

    def _build_xlsx(self, disposal, asset, org):
        wb, ws = create_workbook('Акт ОЗ-3')
        row = 1

        write_info_row(ws, row, 'Акт №:', disposal.document_number); row += 1
        write_info_row(ws, row, 'Дата:', disposal.document_date.strftime('%d.%m.%Y')); row += 1
        write_info_row(ws, row, 'Тип вибуття:', disposal.get_disposal_type_display()); row += 1
        write_info_row(ws, row, 'Інв. номер:', asset.inventory_number); row += 1
        write_info_row(ws, row, 'Назва:', asset.name); row += 1
        write_info_row(ws, row, 'Група:', str(asset.group)); row += 1
        write_info_row(ws, row, 'Рахунок:', asset.group.account_number); row += 1
        write_info_row(ws, row, 'Дата введення:', asset.commissioning_date.strftime('%d.%m.%Y')); row += 1
        write_info_row(ws, row, 'Метод:', asset.get_depreciation_method_display()); row += 1
        write_info_row(ws, row, 'Строк (міс.):', asset.useful_life_months); row += 1
        write_info_row(ws, row, 'МВО:', _responsible_person_display(asset)); row += 1
        row += 1

        # -- Financial --
        write_section_header(ws, row, 'Фінансові дані на дату списання', 2); row += 1
        write_info_row(ws, row, 'Первісна вартість:', float(asset.initial_cost) if asset.initial_cost else 0); row += 1
        write_info_row(ws, row, 'Накопичений знос:', float(disposal.accumulated_depreciation_at_disposal) if disposal.accumulated_depreciation_at_disposal else 0); row += 1
        write_info_row(ws, row, 'Залишкова вартість:', float(disposal.book_value_at_disposal) if disposal.book_value_at_disposal else 0); row += 1
        if disposal.sale_amount and disposal.sale_amount > 0:
            write_info_row(ws, row, 'Сума продажу:', float(disposal.sale_amount)); row += 1
        row += 1

        # -- Reason --
        write_info_row(ws, row, 'Причина списання:', disposal.reason)

        auto_width(ws, 2)
        return workbook_to_response(wb, f'disposal_act_{disposal.document_number}.xlsx')

    def get(self, request, pk):
        disposal = AssetDisposal.objects.select_related(
            'asset', 'asset__group', 'asset__responsible_person',
            'asset__organization', 'asset__location', 'created_by',
        ).get(pk=pk)
        asset = disposal.asset
        org = asset.organization

        fmt = request.query_params.get('export')
        if fmt == 'xlsx':
            return self._build_xlsx(disposal, asset, org)

        styles = _get_styles()
        elements = []

        # -- Official header --
        elements.extend(_form_header_block(
            org, 'ОЗ-3',
            'АКТ списання основних засобiв',
            styles,
        ))

        # -- Approval block --
        elements.extend(_approval_block(org, styles))

        # -- Document info --
        elements.append(Paragraph(
            f'Акт №{disposal.document_number} вiд '
            f'{disposal.document_date.strftime("%d.%m.%Y")}',
            styles['UkrCenter'],
        ))
        elements.append(Spacer(1, 4 * mm))

        # -- Document details --
        doc_rows = [
            ['Тип вибуття:', disposal.get_disposal_type_display()],
        ]
        doc_table = Table(doc_rows, colWidths=[55 * mm, 115 * mm])
        doc_table.setStyle(_header_table_style())
        elements.append(doc_table)
        elements.append(Spacer(1, 4 * mm))

        # -- Asset info --
        elements.append(Paragraph(
            'Вiдомостi про об\'єкт основних засобiв',
            styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 2 * mm))

        asset_rows = [
            ['Iнвентарний номер:', asset.inventory_number],
            ['Назва:', _p(asset.name, styles['UkrNormal'])],
            ['Група ОЗ:', str(asset.group)],
            ['Рахунок облiку:', asset.group.account_number],
            ['Дата введення в експлуатацiю:',
             asset.commissioning_date.strftime('%d.%m.%Y')],
            ['Метод амортизацiї:',
             asset.get_depreciation_method_display()],
            ['Строк корисного використання (мiс.):',
             str(asset.useful_life_months)],
            ['МВО:', _responsible_person_display(asset)],
        ]
        asset_table = Table(asset_rows, colWidths=[55 * mm, 115 * mm])
        asset_table.setStyle(_header_table_style())
        elements.append(asset_table)
        elements.append(Spacer(1, 4 * mm))

        # -- Financial details --
        elements.append(Paragraph(
            'Фiнансовi данi на дату списання', styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 2 * mm))

        fin_rows = [
            ['Первiсна вартiсть, грн:', _fmt(asset.initial_cost)],
            ['Накопичений знос на дату вибуття, грн:',
             _fmt(disposal.accumulated_depreciation_at_disposal)],
            ['Залишкова вартiсть на дату вибуття, грн:',
             _fmt(disposal.book_value_at_disposal)],
        ]
        if disposal.sale_amount and disposal.sale_amount > 0:
            fin_rows.append([
                'Сума продажу, грн:', _fmt(disposal.sale_amount),
            ])
        fin_table = Table(fin_rows, colWidths=[65 * mm, 60 * mm])
        fin_table.setStyle(_header_table_style())
        elements.append(fin_table)
        elements.append(Spacer(1, 4 * mm))

        # -- Commission conclusion / Reason --
        elements.append(Paragraph(
            'Висновок комiсiї / причина списання', styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(disposal.reason, styles['UkrNormal']))

        # -- Notes --
        if disposal.notes:
            elements.append(Spacer(1, 3 * mm))
            elements.append(Paragraph(
                f'Примiтки: {disposal.notes}', styles['UkrNormal'],
            ))

        # -- Commission signatures --
        elements.extend(_commission_signatures_block(None, None, styles))

        # -- Official signatures --
        elements.extend(_official_signatures([
            ('Гол. бухгалтер', org.accountant if org and org.accountant else ''),
            ('Керiвник', org.director if org and org.director else ''),
        ], styles))

        # -- Build PDF --
        buf = io.BytesIO()
        _build_pdf(buf, elements)
        return _make_response(
            buf,
            f'disposal_act_{disposal.document_number}.pdf',
        )


# ============================================================================
# 6. VehicleDisposalActPDFView  --  ОЗ-4 Акт списання автотранспорту
# ============================================================================

class VehicleDisposalActPDFView(APIView):
    """
    ОЗ-4 -- Акт списання автотранспортних засобiв.

    GET /documents/disposal/<pk>/vehicle-act/
    """
    permission_classes = [IsAuthenticated]

    def _build_xlsx(self, disposal, asset, org):
        wb, ws = create_workbook('Акт ОЗ-4')
        row = 1

        write_info_row(ws, row, 'Акт №:', disposal.document_number); row += 1
        write_info_row(ws, row, 'Дата:', disposal.document_date.strftime('%d.%m.%Y')); row += 1
        write_info_row(ws, row, 'Тип вибуття:', disposal.get_disposal_type_display()); row += 1
        write_info_row(ws, row, 'Інв. номер:', asset.inventory_number); row += 1
        write_info_row(ws, row, 'Назва:', asset.name); row += 1
        write_info_row(ws, row, 'Група:', str(asset.group)); row += 1
        write_info_row(ws, row, 'Рахунок:', asset.group.account_number); row += 1
        write_info_row(ws, row, 'Дата введення:', asset.commissioning_date.strftime('%d.%m.%Y')); row += 1
        write_info_row(ws, row, 'Метод:', asset.get_depreciation_method_display()); row += 1
        write_info_row(ws, row, 'Строк (міс.):', asset.useful_life_months); row += 1
        write_info_row(ws, row, 'МВО:', _responsible_person_display(asset)); row += 1
        row += 1

        # -- Vehicle-specific fields --
        write_section_header(ws, row, 'Відомості про автотранспортний засіб', 2); row += 1
        write_info_row(ws, row, 'Рік випуску:', '________________'); row += 1
        write_info_row(ws, row, 'Марка/модель:', '________________'); row += 1
        write_info_row(ws, row, 'Держ. номер:', '________________'); row += 1
        write_info_row(ws, row, 'Двигун:', '________________'); row += 1
        write_info_row(ws, row, 'Шасі:', '________________'); row += 1
        write_info_row(ws, row, 'Кузов:', '________________'); row += 1
        write_info_row(ws, row, 'VIN:', '________________'); row += 1
        write_info_row(ws, row, 'Пробіг (км):', '________________'); row += 1
        row += 1

        # -- Financial --
        write_section_header(ws, row, 'Вартісні дані на дату списання', 2); row += 1
        write_info_row(ws, row, 'Первісна вартість:', float(asset.initial_cost) if asset.initial_cost else 0); row += 1
        write_info_row(ws, row, 'Накопичений знос:', float(disposal.accumulated_depreciation_at_disposal) if disposal.accumulated_depreciation_at_disposal else 0); row += 1
        write_info_row(ws, row, 'Залишкова вартість:', float(disposal.book_value_at_disposal) if disposal.book_value_at_disposal else 0); row += 1
        if disposal.sale_amount and disposal.sale_amount > 0:
            write_info_row(ws, row, 'Сума продажу:', float(disposal.sale_amount)); row += 1
        row += 1

        # -- Reason --
        write_info_row(ws, row, 'Причина списання:', disposal.reason)

        auto_width(ws, 2)
        return workbook_to_response(wb, f'vehicle_disposal_{disposal.document_number}.xlsx')

    def get(self, request, pk):
        disposal = AssetDisposal.objects.select_related(
            'asset', 'asset__group', 'asset__responsible_person',
            'asset__organization', 'asset__location', 'created_by',
        ).get(pk=pk)
        asset = disposal.asset
        org = asset.organization

        fmt = request.query_params.get('export')
        if fmt == 'xlsx':
            return self._build_xlsx(disposal, asset, org)

        styles = _get_styles()
        elements = []

        # -- Official header --
        elements.extend(_form_header_block(
            org, 'ОЗ-4',
            'АКТ списання автотранспортних засобiв',
            styles,
        ))

        # -- Approval block --
        elements.extend(_approval_block(org, styles))

        # -- Document info --
        elements.append(Paragraph(
            f'Акт №{disposal.document_number} вiд '
            f'{disposal.document_date.strftime("%d.%m.%Y")}',
            styles['UkrCenter'],
        ))
        elements.append(Spacer(1, 4 * mm))

        # -- Section 1: General vehicle info --
        elements.append(Paragraph(
            'I. Загальнi вiдомостi про автотранспортний засiб',
            styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 2 * mm))

        vehicle_rows = [
            ['Назва:', _p(asset.name, styles['UkrNormal'])],
            ['Iнвентарний номер:', asset.inventory_number],
            ['Група ОЗ:', str(asset.group)],
            ['Дата введення в експлуатацiю:',
             asset.commissioning_date.strftime('%d.%m.%Y')],
            ['Рiк випуску:', '________________'],
            ['Марка, модель:', '________________'],
            ['Державний номерний знак:', '________________'],
            ['Номер двигуна:', '________________'],
            ['Номер шасi (рами):', '________________'],
            ['Номер кузова:', '________________'],
            ['VIN-код:', '________________'],
            ['Пробiг з початку експлуатацiї, км:', '________________'],
            ['МВО:', _responsible_person_display(asset)],
        ]
        vehicle_table = Table(vehicle_rows, colWidths=[65 * mm, 105 * mm])
        vehicle_table.setStyle(_header_table_style())
        elements.append(vehicle_table)
        elements.append(Spacer(1, 4 * mm))

        # -- Section 2: Financial data --
        elements.append(Paragraph(
            'II. Вартiснi данi на дату списання', styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 2 * mm))

        fin_rows = [
            ['Первiсна вартiсть, грн:', _fmt(asset.initial_cost)],
            ['Накопичений знос, грн:',
             _fmt(disposal.accumulated_depreciation_at_disposal)],
            ['Залишкова вартiсть, грн:',
             _fmt(disposal.book_value_at_disposal)],
        ]
        if disposal.sale_amount and disposal.sale_amount > 0:
            fin_rows.append([
                'Сума продажу, грн:', _fmt(disposal.sale_amount),
            ])
        fin_table = Table(fin_rows, colWidths=[65 * mm, 60 * mm])
        fin_table.setStyle(_header_table_style())
        elements.append(fin_table)
        elements.append(Spacer(1, 4 * mm))

        # -- Section 3: Reason --
        elements.append(Paragraph(
            'III. Причина списання', styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(disposal.reason, styles['UkrNormal']))
        elements.append(Spacer(1, 4 * mm))

        # -- Section 4: Commission conclusion --
        elements.append(Paragraph(
            'IV. Висновок комiсiї', styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(
            '________________________________________________________________________<br/>'
            '________________________________________________________________________<br/>'
            '________________________________________________________________________',
            styles['UkrNormal'],
        ))
        elements.append(Spacer(1, 4 * mm))

        # -- Section 5: Disposal results --
        elements.append(Paragraph(
            'V. Результати списання', styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 2 * mm))

        result_rows = [
            ['Виручка вiд реалiзацiї матерiалiв, грн:', '________________'],
            ['Витрати на лiквiдацiю, грн:', '________________'],
            ['Фiнансовий результат, грн:', '________________'],
        ]
        result_table = Table(result_rows, colWidths=[65 * mm, 60 * mm])
        result_table.setStyle(_header_table_style())
        elements.append(result_table)

        # -- Notes --
        if disposal.notes:
            elements.append(Spacer(1, 3 * mm))
            elements.append(Paragraph(
                f'Примiтки: {disposal.notes}', styles['UkrNormal'],
            ))

        # -- Commission signatures --
        elements.extend(_commission_signatures_block(None, None, styles))

        # -- Official signatures --
        elements.extend(_official_signatures([
            ('Гол. бухгалтер', org.accountant if org and org.accountant else ''),
            ('Керiвник', org.director if org and org.director else ''),
        ], styles))

        # -- Build PDF --
        buf = io.BytesIO()
        _build_pdf(buf, elements)
        return _make_response(
            buf,
            f'vehicle_disposal_{disposal.document_number}.pdf',
        )


# ============================================================================
# 7. AccountEntriesReportPDFView  --  Журнал проводок
# ============================================================================

class AccountEntriesReportPDFView(APIView):
    """
    Журнал проводок за перiод.

    GET /documents/entries-report/?date_from=2025-01-01&date_to=2025-03-31
    """
    permission_classes = [IsAuthenticated]

    def _build_xlsx(self, qs, date_from_str, date_to_str):
        wb, ws = create_workbook('Журнал проводок')
        row = 1

        headers = ['Дата', 'Дт', 'Кт', 'Сума', 'Опис', 'ОЗ']
        write_header_row(ws, row, headers); row += 1
        money = {4}

        total_amount = Decimal('0.00')

        for entry in qs:
            write_data_row(ws, row, [
                entry.date.strftime('%d.%m.%Y'),
                entry.debit_account,
                entry.credit_account,
                float(entry.amount) if entry.amount else 0,
                entry.description[:60],
                str(entry.asset)[:35],
            ], money_cols=money)
            row += 1
            total_amount += entry.amount

        write_total_row(ws, row, [
            '', '', '', float(total_amount), 'РАЗОМ', '',
        ], money_cols=money)

        auto_width(ws, 6)

        fn_parts = ['entries_report']
        if date_from_str:
            fn_parts.append(date_from_str)
        if date_to_str:
            fn_parts.append(date_to_str)
        filename = '_'.join(fn_parts) + '.xlsx'

        return workbook_to_response(wb, filename)

    def get(self, request):
        date_from_str = request.query_params.get('date_from')
        date_to_str = request.query_params.get('date_to')

        qs = AccountEntry.objects.select_related(
            'asset',
        ).order_by('date', 'pk')

        if date_from_str:
            qs = qs.filter(date__gte=date_from_str)
        if date_to_str:
            qs = qs.filter(date__lte=date_to_str)

        fmt = request.query_params.get('export')
        if fmt == 'xlsx':
            return self._build_xlsx(qs, date_from_str, date_to_str)

        styles = _get_styles()
        elements = []

        # -- Title --
        elements.append(Paragraph(
            'Журнал проводок', styles['UkrTitle'],
        ))

        period_label = ''
        if date_from_str and date_to_str:
            period_label = f'за перiод з {date_from_str} по {date_to_str}'
        elif date_from_str:
            period_label = f'з {date_from_str}'
        elif date_to_str:
            period_label = f'по {date_to_str}'
        if period_label:
            elements.append(Paragraph(period_label, styles['UkrSubtitle']))
        elements.append(Spacer(1, 4 * mm))

        # -- Data table --
        header = [
            _p('Дата', styles['UkrSmall']),
            _p('Дт', styles['UkrSmall']),
            _p('Кт', styles['UkrSmall']),
            _p('Сума, грн', styles['UkrSmall']),
            _p('Опис', styles['UkrSmall']),
            _p('ОЗ', styles['UkrSmall']),
        ]
        data = [header]

        total_amount = Decimal('0.00')

        for entry in qs:
            data.append([
                entry.date.strftime('%d.%m.%Y'),
                entry.debit_account,
                entry.credit_account,
                _fmt(entry.amount),
                _p(entry.description[:60], styles['UkrSmall']),
                _p(str(entry.asset)[:35], styles['UkrSmall']),
            ])
            total_amount += entry.amount

        # Summary row
        data.append([
            '', '', '',
            _fmt(total_amount),
            _p('РАЗОМ', styles['UkrSmall']),
            '',
        ])

        col_widths = [
            20 * mm, 14 * mm, 14 * mm, 25 * mm, 55 * mm, 45 * mm,
        ]
        table = Table(data, colWidths=col_widths)
        ts = _data_table_style()
        ts.add('ALIGN', (3, 1), (3, -1), 'RIGHT')
        ts.add('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.93, 0.93, 0.93))
        table.setStyle(ts)
        elements.append(table)

        # -- Footer --
        elements.append(Spacer(1, 5 * mm))
        elements.append(Paragraph(
            f'Всього проводок: {qs.count()}',
            styles['UkrNormal'],
        ))
        elements.append(Paragraph(
            f'Загальна сума: {_fmt(total_amount)} грн',
            styles['UkrNormal'],
        ))

        # -- Build PDF --
        buf = io.BytesIO()
        _build_pdf(buf, elements)

        fn_parts = ['entries_report']
        if date_from_str:
            fn_parts.append(date_from_str)
        if date_to_str:
            fn_parts.append(date_to_str)
        filename = '_'.join(fn_parts) + '.pdf'

        return _make_response(buf, filename)


# ============================================================================
# 8. TurnoverStatementPDFView  --  Оборотна відомість
#    Наказ Міністерства фінансів України 5 лютого 2021 року №101
# ============================================================================

class TurnoverStatementPDFView(APIView):
    """
    Оборотна вiдомiсть за перiод.

    Форма згiдно з Наказом Мiнiстерства фiнансiв України 5 лютого 2021 року №101.

    GET /documents/turnover-statement/?date_from=2025-01-01&date_to=2025-12-31
    """
    permission_classes = [IsAuthenticated]

    def _build_xlsx(self, assets, date_from, date_to, date_from_str, date_to_str):
        wb, ws = create_workbook('Оборотна відомість')
        row = 1

        headers = [
            '№ з/п', 'МВО', 'Рахунок', 'Найменування',
            'Номенкл.номер', 'Од.виміру', 'Вартість',
            'Залишок (к-ть)', 'Залишок (сума)',
            'Дебет (к-ть)', 'Дебет (сума)',
            'Кредит (к-ть)', 'Кредит (сума)',
            'Залишок кін. (к-ть)', 'Залишок кін. (сума)',
            'Відмітки',
        ]
        write_header_row(ws, row, headers); row += 1
        money = {7, 9, 11, 13, 15}

        grand_open_qty = 0
        grand_open_sum = Decimal('0.00')
        grand_debit_qty = 0
        grand_debit_sum = Decimal('0.00')
        grand_credit_qty = 0
        grand_credit_sum = Decimal('0.00')
        grand_close_qty = 0
        grand_close_sum = Decimal('0.00')

        for idx, asset in enumerate(assets, 1):
            if asset.commissioning_date < date_from:
                open_qty = asset.quantity
                open_sum = asset.initial_cost
            else:
                open_qty = 0
                open_sum = Decimal('0.00')

            receipts_in_period = AssetReceipt.objects.filter(
                asset=asset,
                document_date__gte=date_from,
                document_date__lte=date_to,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            improvements_in_period = AssetImprovement.objects.filter(
                asset=asset,
                date__gte=date_from,
                date__lte=date_to,
                increases_value=True,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            debit_sum = receipts_in_period + improvements_in_period
            debit_qty = 0
            if date_from <= asset.commissioning_date <= date_to:
                debit_qty = asset.quantity

            disposals_in_period = AssetDisposal.objects.filter(
                asset=asset,
                document_date__gte=date_from,
                document_date__lte=date_to,
            ).aggregate(total=Sum('book_value_at_disposal'))['total'] or Decimal('0.00')

            depreciation_in_period = DepreciationRecord.objects.filter(
                asset=asset,
            ).filter(
                Q(period_year__gt=date_from.year) |
                Q(period_year=date_from.year, period_month__gte=date_from.month),
            ).filter(
                Q(period_year__lt=date_to.year) |
                Q(period_year=date_to.year, period_month__lte=date_to.month),
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            credit_sum = disposals_in_period + depreciation_in_period
            credit_qty = 0
            if asset.disposal_date and date_from <= asset.disposal_date <= date_to:
                credit_qty = asset.quantity

            close_sum = open_sum + debit_sum - credit_sum
            close_qty = open_qty + debit_qty - credit_qty

            mvo = _responsible_person_display(asset)

            write_data_row(ws, row, [
                idx,
                mvo[:25],
                asset.group.account_number if asset.group else '',
                asset.name[:35],
                asset.inventory_number,
                asset.unit_of_measure or 'шт.',
                float(asset.initial_cost),
                open_qty,
                float(open_sum),
                debit_qty if debit_qty else '',
                float(debit_sum) if debit_sum else '',
                credit_qty if credit_qty else '',
                float(credit_sum) if credit_sum else '',
                close_qty,
                float(close_sum),
                '',
            ], money_cols=money)
            row += 1

            grand_open_qty += open_qty
            grand_open_sum += open_sum
            grand_debit_qty += debit_qty
            grand_debit_sum += debit_sum
            grand_credit_qty += credit_qty
            grand_credit_sum += credit_sum
            grand_close_qty += close_qty
            grand_close_sum += close_sum

        write_total_row(ws, row, [
            '', '', '', 'РАЗОМ:', '', '', '',
            grand_open_qty,
            float(grand_open_sum),
            grand_debit_qty if grand_debit_qty else '',
            float(grand_debit_sum) if grand_debit_sum else '',
            grand_credit_qty if grand_credit_qty else '',
            float(grand_credit_sum) if grand_credit_sum else '',
            grand_close_qty,
            float(grand_close_sum),
            '',
        ], money_cols=money)

        auto_width(ws, 16)
        return workbook_to_response(
            wb, f'turnover_statement_{date_from_str}_{date_to_str}.xlsx',
        )

    def get(self, request):
        date_from_str = request.query_params.get('date_from')
        date_to_str = request.query_params.get('date_to')

        if not date_from_str or not date_to_str:
            return HttpResponse(
                'Parameters date_from and date_to are required.',
                status=400,
            )

        date_from = date.fromisoformat(date_from_str)
        date_to = date.fromisoformat(date_to_str)

        # Query all assets that were active at any point during the period.
        # An asset is relevant if:
        # - it was commissioned on or before date_to, AND
        # - it was not disposed before date_from (or was never disposed)
        assets = Asset.objects.filter(
            commissioning_date__lte=date_to,
        ).filter(
            Q(disposal_date__isnull=True) | Q(disposal_date__gte=date_from)
        ).select_related(
            'group', 'responsible_person', 'organization', 'location',
        ).order_by('group__account_number', 'inventory_number')

        fmt = request.query_params.get('export')
        if fmt == 'xlsx':
            return self._build_xlsx(assets, date_from, date_to, date_from_str, date_to_str)

        org = _get_org_from_request_or_default(request)
        if assets.exists():
            first_asset = assets.first()
            if first_asset.organization:
                org = first_asset.organization

        styles = _get_styles()
        elements = []

        # -- Official header (landscape) --
        approval_text = (
            'Наказ Мiнiстерства фiнансiв України\n'
            '5 лютого 2021 року №101'
        )
        elements.extend(_form_header_block_landscape(
            org,
            'ОБОРОТНА ВIДОМIСТЬ',
            styles,
            approval_text=approval_text,
        ))

        elements.append(Paragraph(
            f'за перiод з {date_from_str} по {date_to_str}',
            styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 4 * mm))

        # -- Data table (16 columns) --
        # Three-level header as per Наказ МФУ №101
        header_row1 = [
            _p('№<br/>з/п', styles['UkrSmallCenter']),
            _p('Матерiально<br/>вiдповiдальна<br/>особа', styles['UkrSmallCenter']),
            _p('Номер рахунку,<br/>субрахунку<br/>(аналiтичного<br/>рахунку)', styles['UkrSmallCenter']),
            _p('Найменування', styles['UkrSmallCenter']),
            _p('Номенклатурний<br/>номер*', styles['UkrSmallCenter']),
            _p('Одиниця<br/>вимiру', styles['UkrSmallCenter']),
            _p('Вартiсть', styles['UkrSmallCenter']),
            _p('Залишок', styles['UkrSmallCenter']),
            '',  # merged with col 7
            _p('Оборот', styles['UkrSmallCenter']),
            '',  # merged
            '',  # merged
            '',  # merged
            _p('Залишок', styles['UkrSmallCenter']),
            '',  # merged with col 13
            _p('Вiдмiтки', styles['UkrSmallCenter']),
        ]

        header_row2 = [
            '', '', '',
            _p('або однорiдна<br/>група (вид)', styles['UkrSmallCenter']),
            '', '', '',
            _p(f'на {date_from_str}', styles['UkrSmallCenter']),
            '',  # merged with col 7
            _p('дебет', styles['UkrSmallCenter']),
            '',  # merged with col 9
            _p('кредит', styles['UkrSmallCenter']),
            '',  # merged with col 11
            _p(f'на {date_to_str}', styles['UkrSmallCenter']),
            '',  # merged with col 13
            '',
        ]

        header_row3 = [
            '', '', '', '', '', '', '',
            _p('кiлькiсть', styles['UkrSmallCenter']),
            _p('сума', styles['UkrSmallCenter']),
            _p('кiлькiсть', styles['UkrSmallCenter']),
            _p('сума', styles['UkrSmallCenter']),
            _p('кiлькiсть', styles['UkrSmallCenter']),
            _p('сума', styles['UkrSmallCenter']),
            _p('кiлькiсть', styles['UkrSmallCenter']),
            _p('сума', styles['UkrSmallCenter']),
            '',
        ]

        # Column numbers row
        col_num_row = [
            _p(str(i), styles['UkrSmallCenter']) for i in range(1, 17)
        ]

        data = [header_row1, header_row2, header_row3, col_num_row]

        # Totals accumulators
        grand_open_qty = 0
        grand_open_sum = Decimal('0.00')
        grand_debit_qty = 0
        grand_debit_sum = Decimal('0.00')
        grand_credit_qty = 0
        grand_credit_sum = Decimal('0.00')
        grand_close_qty = 0
        grand_close_sum = Decimal('0.00')

        for idx, asset in enumerate(assets, 1):
            # Opening balance: asset existed before date_from
            if asset.commissioning_date < date_from:
                open_qty = asset.quantity
                open_sum = asset.initial_cost
            else:
                open_qty = 0
                open_sum = Decimal('0.00')

            # Debit turnover: receipts + value-increasing improvements in period
            receipts_in_period = AssetReceipt.objects.filter(
                asset=asset,
                document_date__gte=date_from,
                document_date__lte=date_to,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            improvements_in_period = AssetImprovement.objects.filter(
                asset=asset,
                date__gte=date_from,
                date__lte=date_to,
                increases_value=True,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            debit_sum = receipts_in_period + improvements_in_period
            # If asset was commissioned within the period, count qty as debit
            debit_qty = 0
            if date_from <= asset.commissioning_date <= date_to:
                debit_qty = asset.quantity

            # Credit turnover: disposals + depreciation in period
            disposals_in_period = AssetDisposal.objects.filter(
                asset=asset,
                document_date__gte=date_from,
                document_date__lte=date_to,
            ).aggregate(total=Sum('book_value_at_disposal'))['total'] or Decimal('0.00')

            depreciation_in_period = DepreciationRecord.objects.filter(
                asset=asset,
                period_year__gte=date_from.year,
                period_month__gte=date_from.month if date_from.year == date_to.year else 1,
            ).filter(
                period_year__lte=date_to.year,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            # More precise depreciation filtering
            depreciation_in_period = DepreciationRecord.objects.filter(
                asset=asset,
            ).filter(
                # Within the date range (year*100+month comparison)
                Q(period_year__gt=date_from.year) |
                Q(period_year=date_from.year, period_month__gte=date_from.month),
            ).filter(
                Q(period_year__lt=date_to.year) |
                Q(period_year=date_to.year, period_month__lte=date_to.month),
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            credit_sum = disposals_in_period + depreciation_in_period
            credit_qty = 0
            if asset.disposal_date and date_from <= asset.disposal_date <= date_to:
                credit_qty = asset.quantity

            # Closing balance = opening + debit - credit
            close_sum = open_sum + debit_sum - credit_sum
            close_qty = open_qty + debit_qty - credit_qty

            # MVO name
            mvo = _responsible_person_display(asset)

            data.append([
                str(idx),
                _p(mvo[:25], styles['UkrSmall']),
                asset.group.account_number if asset.group else '',
                _p(asset.name[:35], styles['UkrSmall']),
                asset.inventory_number,
                asset.unit_of_measure or 'шт.',
                _fmt(asset.initial_cost),
                str(open_qty),
                _fmt(open_sum),
                str(debit_qty) if debit_qty else '',
                _fmt(debit_sum) if debit_sum else '-',
                str(credit_qty) if credit_qty else '',
                _fmt(credit_sum) if credit_sum else '-',
                str(close_qty),
                _fmt(close_sum),
                '',
            ])

            grand_open_qty += open_qty
            grand_open_sum += open_sum
            grand_debit_qty += debit_qty
            grand_debit_sum += debit_sum
            grand_credit_qty += credit_qty
            grand_credit_sum += credit_sum
            grand_close_qty += close_qty
            grand_close_sum += close_sum

        # Totals row
        data.append([
            '', '', '', _p('РАЗОМ:', styles['UkrSmall']),
            '', '', '',
            str(grand_open_qty),
            _fmt(grand_open_sum),
            str(grand_debit_qty) if grand_debit_qty else '',
            _fmt(grand_debit_sum) if grand_debit_sum else '-',
            str(grand_credit_qty) if grand_credit_qty else '',
            _fmt(grand_credit_sum) if grand_credit_sum else '-',
            str(grand_close_qty),
            _fmt(grand_close_sum),
            '',
        ])

        page_w = landscape(A4)[0] - 24 * mm
        col_widths = [
            page_w * 0.03,   # 1  - № з/п
            page_w * 0.09,   # 2  - МВО
            page_w * 0.05,   # 3  - Рахунок
            page_w * 0.12,   # 4  - Найменування
            page_w * 0.065,  # 5  - Номенкл. номер
            page_w * 0.035,  # 6  - Од. виміру
            page_w * 0.065,  # 7  - Вартість
            page_w * 0.035,  # 8  - Залишок на початок к-ть
            page_w * 0.075,  # 9  - Залишок на початок сума
            page_w * 0.035,  # 10 - Оборот дебет к-ть
            page_w * 0.075,  # 11 - Оборот дебет сума
            page_w * 0.035,  # 12 - Оборот кредит к-ть
            page_w * 0.075,  # 13 - Оборот кредит сума
            page_w * 0.035,  # 14 - Залишок на кінець к-ть
            page_w * 0.075,  # 15 - Залишок на кінець сума
            page_w * 0.04,   # 16 - Відмітки
        ]

        table = Table(data, colWidths=col_widths)
        ts = _data_table_style(header_rows=4)
        # Row 0: merge paired/grouped columns
        ts.add('SPAN', (7, 0), (8, 0))    # Залишок (початок)
        ts.add('SPAN', (9, 0), (12, 0))   # Оборот (all 4 cols)
        ts.add('SPAN', (13, 0), (14, 0))  # Залишок (кінець)
        # Row 1: merge sub-headers
        ts.add('SPAN', (7, 1), (8, 1))    # на [date_from]
        ts.add('SPAN', (9, 1), (10, 1))   # дебет
        ts.add('SPAN', (11, 1), (12, 1))  # кредит
        ts.add('SPAN', (13, 1), (14, 1))  # на [date_to]
        # Merge single-cell headers vertically across rows 0-2
        for c in (0, 1, 2, 4, 5, 6):
            ts.add('SPAN', (c, 0), (c, 2))
        # Col 3 (Найменування) spans rows 0-1
        ts.add('SPAN', (3, 0), (3, 1))
        # Col 15 (Відмітки) spans rows 0-2
        ts.add('SPAN', (15, 0), (15, 2))

        ts.add('ALIGN', (6, 4), (-2, -1), 'RIGHT')
        ts.add('ALIGN', (0, 4), (0, -1), 'CENTER')
        ts.add('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.93, 0.93, 0.93))
        ts.add('FONTSIZE', (0, -1), (-1, -1), 8)
        table.setStyle(ts)
        elements.append(table)

        # -- Footer --
        elements.append(Spacer(1, 5 * mm))
        elements.append(Paragraph(
            f'Всього позицiй: {assets.count()}',
            styles['UkrNormal'],
        ))

        # -- Signatures --
        elements.extend(_official_signatures([
            ('Головний бухгалтер',
             org.accountant if org and org.accountant else ''),
            ('Виконавець', ''),
        ], styles))

        # -- Build PDF --
        buf = io.BytesIO()
        _build_pdf(buf, elements, pagesize=landscape(A4))

        return _make_response(
            buf,
            f'turnover_statement_{date_from_str}_{date_to_str}.pdf',
        )
