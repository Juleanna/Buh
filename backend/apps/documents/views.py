"""
Генерація PDF-документів для обліку основних засобів.

Типові форми Мінфіну України:
- ОЗ-1: Акт приймання-передачі (внутрішнього переміщення) основних засобів
- ОЗ-3: Акт списання основних засобів
- ОЗ-4: Акт списання автотранспортних засобів
- ОЗ-6: Інвентарна картка обліку основних засобів
- Інв-1: Інвентаризаційний опис основних засобів

Додатково:
- Відомість нарахування амортизації
- Журнал проводок
"""
import io
import os
from datetime import datetime
from decimal import Decimal

from django.http import HttpResponse
from django.db.models import Sum
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


# ---------------------------------------------------------------------------
# Official form helpers
# ---------------------------------------------------------------------------

def _form_header_block(org, form_number, form_name, styles):
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
    right_lines = (
        f'Типова форма №{form_number}<br/>'
        f'ЗАТВЕРДЖЕНО<br/>'
        f'{APPROVAL_ORDER.replace(chr(10), "<br/>")}<br/>'
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


# ============================================================================
# 1. AssetCardPDFView  --  ОЗ-6 Інвентарна картка обліку ОЗ
# ============================================================================

class AssetCardPDFView(APIView):
    """
    ОЗ-6 -- Iнвентарна картка облiку основних засобiв.

    GET /documents/asset/<pk>/card/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        asset = Asset.objects.select_related(
            'group', 'responsible_person', 'organization',
        ).get(pk=pk)

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
                asset.disposal_date.strftime('%d.%m.%Y') if asset.disposal_date else '—',
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
            ['МВО:', (asset.responsible_person.get_full_name()
                      if asset.responsible_person else '—')],
            ['Мiсцезнаходження:', asset.location or '—'],
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
# ============================================================================

class DepreciationReportPDFView(APIView):
    """
    Вiдомiсть нарахування амортизацiї за мiсяць.

    GET /documents/depreciation-report/?year=2025&month=3
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year = int(request.query_params.get('year', datetime.now().year))
        month = int(request.query_params.get('month', datetime.now().month))

        records = DepreciationRecord.objects.filter(
            period_year=year, period_month=month,
        ).select_related(
            'asset', 'asset__group',
        ).order_by('asset__inventory_number')

        styles = _get_styles()
        elements = []

        # -- Title --
        elements.append(Paragraph(
            f'Вiдомiсть нарахування амортизацiї',
            styles['UkrTitle'],
        ))
        elements.append(Paragraph(
            f'за {month:02d}.{year}',
            styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 4 * mm))

        # -- Data table --
        header = [
            _p('№п/п', styles['UkrSmall']),
            _p('Iнв.номер', styles['UkrSmall']),
            _p('Назва', styles['UkrSmall']),
            _p('Група', styles['UkrSmall']),
            _p('Метод', styles['UkrSmall']),
            _p('Вартiсть до, грн', styles['UkrSmall']),
            _p('Сума амортизацiї, грн', styles['UkrSmall']),
            _p('Вартiсть пiсля, грн', styles['UkrSmall']),
        ]
        data = [header]

        total_amount = Decimal('0.00')
        total_before = Decimal('0.00')
        total_after = Decimal('0.00')

        for i, rec in enumerate(records, 1):
            data.append([
                str(i),
                rec.asset.inventory_number,
                _p(rec.asset.name[:40], styles['UkrSmall']),
                rec.asset.group.code,
                rec.get_depreciation_method_display()[:18],
                _fmt(rec.book_value_before),
                _fmt(rec.amount),
                _fmt(rec.book_value_after),
            ])
            total_amount += rec.amount
            total_before += rec.book_value_before
            total_after += rec.book_value_after

        # Summary row
        data.append([
            '', '', '', '',
            _p('РАЗОМ:', styles['UkrSmall']),
            _fmt(total_before),
            _fmt(total_amount),
            _fmt(total_after),
        ])

        col_widths = [
            9 * mm, 22 * mm, 42 * mm, 14 * mm,
            28 * mm, 25 * mm, 27 * mm, 25 * mm,
        ]
        table = Table(data, colWidths=col_widths)
        ts = _data_table_style()
        ts.add('ALIGN', (5, 1), (-1, -1), 'RIGHT')
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

        # -- Build PDF --
        buf = io.BytesIO()
        _build_pdf(buf, elements)
        return _make_response(
            buf,
            f'depreciation_report_{year}_{month:02d}.pdf',
        )


# ============================================================================
# 3. InventoryReportPDFView  --  Інв-1 Інвентаризаційний опис ОЗ
# ============================================================================

class InventoryReportPDFView(APIView):
    """
    Iнв-1 -- Iнвентаризацiйний опис основних засобiв.

    GET /documents/inventory/<pk>/report/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        inventory = Inventory.objects.prefetch_related(
            'items__asset__group', 'commission_members',
        ).select_related('commission_head').get(pk=pk)

        items = inventory.items.select_related(
            'asset', 'asset__group', 'asset__organization',
        ).order_by('asset__inventory_number')

        # Detect organization from first item
        org = None
        first_item = items.first()
        if first_item and first_item.asset.organization:
            org = first_item.asset.organization

        styles = _get_styles()
        elements = []

        # -- Official header --
        elements.extend(_form_header_block(
            org, 'Iнв-1',
            'IНВЕНТАРИЗАЦIЙНИЙ ОПИС основних засобiв',
            styles,
        ))

        # -- Inventory header info --
        inv_rows = [
            ['Номер iнвентаризацiї:', inventory.number],
            ['Дата iнвентаризацiї:',
             inventory.date.strftime('%d.%m.%Y')],
            ['Наказ:', f'№{inventory.order_number} вiд '
                       f'{inventory.order_date.strftime("%d.%m.%Y")}'],
            ['Мiсце проведення:', inventory.location or '—'],
            ['Статус:', inventory.get_status_display()],
        ]
        inv_table = Table(inv_rows, colWidths=[55 * mm, 115 * mm])
        inv_table.setStyle(_header_table_style())
        elements.append(inv_table)
        elements.append(Spacer(1, 5 * mm))

        # -- Items table --
        header = [
            _p('№п/п', styles['UkrSmall']),
            _p('Iнв.номер', styles['UkrSmall']),
            _p('Назва', styles['UkrSmall']),
            _p('Облiкова вартiсть, грн', styles['UkrSmall']),
            _p('Факт.наявнiсть', styles['UkrSmall']),
            _p('Стан', styles['UkrSmall']),
            _p('Рiзниця, грн', styles['UkrSmall']),
        ]
        data = [header]

        total_book = Decimal('0.00')
        total_diff = Decimal('0.00')
        found_count = 0
        shortage_count = 0

        for i, item in enumerate(items, 1):
            data.append([
                str(i),
                item.asset.inventory_number,
                _p(item.asset.name[:35], styles['UkrSmall']),
                _fmt(item.book_value),
                'Так' if item.is_found else 'НI',
                item.get_condition_display()[:15],
                _fmt(item.difference),
            ])
            total_book += item.book_value
            total_diff += item.difference
            if item.is_found:
                found_count += 1
            else:
                shortage_count += 1

        total_items = items.count()

        # Summary row
        data.append([
            '', '', _p('РАЗОМ:', styles['UkrSmall']),
            _fmt(total_book), '', '', _fmt(total_diff),
        ])

        col_widths = [
            9 * mm, 22 * mm, 45 * mm, 30 * mm,
            25 * mm, 22 * mm, 25 * mm,
        ]
        table = Table(data, colWidths=col_widths)
        ts = _data_table_style()
        ts.add('ALIGN', (3, 1), (3, -1), 'RIGHT')
        ts.add('ALIGN', (6, 1), (6, -1), 'RIGHT')
        ts.add('ALIGN', (4, 1), (4, -1), 'CENTER')
        ts.add('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.93, 0.93, 0.93))
        table.setStyle(ts)
        elements.append(table)

        # -- Summary block --
        elements.append(Spacer(1, 5 * mm))
        elements.append(Paragraph(
            'Пiдсумки iнвентаризацiї', styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 2 * mm))

        summary_rows = [
            ['Всього позицiй:', str(total_items)],
            ['Знайдено:', str(found_count)],
            ['Нестачi:', str(shortage_count)],
            ['Загальна облiкова вартiсть, грн:', _fmt(total_book)],
            ['Загальна рiзниця, грн:', _fmt(total_diff)],
        ]
        summary_table = Table(summary_rows, colWidths=[55 * mm, 50 * mm])
        summary_table.setStyle(_header_table_style())
        elements.append(summary_table)

        # -- Commission signatures (individual lines) --
        members = inventory.commission_members.all()
        elements.extend(_commission_signatures_block(
            inventory.commission_head, members, styles,
        ))

        # -- MVO signature --
        elements.append(Spacer(1, 8 * mm))
        mvo_data = [[
            _p('Матерiально вiдповiдальна особа:', styles['UkrSignature']),
            '____________',
            '________________',
        ]]
        mvo_table = Table(mvo_data, colWidths=[60 * mm, 35 * mm, 60 * mm])
        mvo_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ]))
        elements.append(mvo_table)

        # -- Date line --
        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph(
            f'Дата складання iнвентаризацiйного опису: '
            f'{inventory.date.strftime("%d.%m.%Y")}',
            styles['UkrNormal'],
        ))

        # -- Build PDF --
        buf = io.BytesIO()
        _build_pdf(buf, elements)
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

    def get(self, request, pk):
        receipt = AssetReceipt.objects.select_related(
            'asset', 'asset__group', 'asset__responsible_person',
            'asset__organization', 'created_by',
        ).get(pk=pk)
        asset = receipt.asset
        org = asset.organization

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
            ['Постачальник / джерело:', receipt.supplier or '—'],
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
            ['Мiсцезнаходження:', asset.location or '—'],
            ['МВО:', (asset.responsible_person.get_full_name()
                      if asset.responsible_person else '—')],
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
            ('Прийняв', (asset.responsible_person.get_full_name()
                         if asset.responsible_person else '')),
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

    def get(self, request, pk):
        disposal = AssetDisposal.objects.select_related(
            'asset', 'asset__group', 'asset__responsible_person',
            'asset__organization', 'created_by',
        ).get(pk=pk)
        asset = disposal.asset
        org = asset.organization

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
            ['МВО:', (asset.responsible_person.get_full_name()
                      if asset.responsible_person else '—')],
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

    def get(self, request, pk):
        disposal = AssetDisposal.objects.select_related(
            'asset', 'asset__group', 'asset__responsible_person',
            'asset__organization', 'created_by',
        ).get(pk=pk)
        asset = disposal.asset
        org = asset.organization

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
            ['МВО:', (asset.responsible_person.get_full_name()
                      if asset.responsible_person else '—')],
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
