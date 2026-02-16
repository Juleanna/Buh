"""
Генерація PDF-документів для обліку основних засобів:
- ОЗ-1: Інвентарна картка обліку ОЗ
- ОЗ-1: Акт приймання-передачі ОЗ
- ОЗ-3: Акт списання ОЗ
- ОЗ-6: Відомість нарахування амортизації
- Інв-1: Інвентаризаційний опис ОЗ
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


# ============================================================================
# 1. AssetCardPDFView  --  ОЗ-1 Інвентарна картка обліку ОЗ
# ============================================================================

class AssetCardPDFView(APIView):
    """
    ОЗ-1 — Інвентарна картка обліку основних засобів.

    GET /documents/asset/<pk>/card/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        asset = Asset.objects.select_related(
            'group', 'responsible_person', 'organization',
        ).get(pk=pk)

        styles = _get_styles()
        elements = []

        # -- Title --
        elements.append(Paragraph(
            'Iнвентарна картка облiку основних засобiв (ОЗ-1)',
            styles['UkrTitle'],
        ))
        elements.append(Spacer(1, 2 * mm))

        if asset.organization:
            elements.append(Paragraph(
                f'Пiдприємство: {asset.organization}',
                styles['UkrCenter'],
            ))
            elements.append(Spacer(1, 2 * mm))

        # -- Main asset data (two-column key/value) --
        info_rows = [
            ['Iнвентарний номер:', asset.inventory_number],
            ['Назва:', asset.name],
            ['Група ОЗ:', str(asset.group)],
            ['Рахунок облiку:', asset.group.account_number],
            ['Рахунок зносу:', asset.group.depreciation_account],
            ['Статус:', asset.get_status_display()],
            ['Дата введення в експлуатацiю:',
             asset.commissioning_date.strftime('%d.%m.%Y')],
            ['Дата початку амортизацiї:',
             asset.depreciation_start_date.strftime('%d.%m.%Y')],
            ['Дата вибуття:',
             asset.disposal_date.strftime('%d.%m.%Y') if asset.disposal_date else '-'],
        ]
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

        # -- Responsible person & location --
        elements.append(Paragraph(
            'Вiдповiдальна особа та мiсцезнаходження',
            styles['UkrSubtitle'],
        ))
        resp_rows = [
            ['МВО:', (asset.responsible_person.get_full_name()
                      if asset.responsible_person else '-')],
            ['Мiсцезнаходження:', asset.location or '-'],
        ]
        if asset.description:
            resp_rows.append(['Опис / характеристики:', asset.description])
        resp_table = Table(resp_rows, colWidths=[65 * mm, 105 * mm])
        resp_table.setStyle(_header_table_style())
        elements.append(resp_table)
        elements.append(Spacer(1, 6 * mm))

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

        # -- Build PDF --
        buf = io.BytesIO()
        _build_pdf(buf, elements)
        return _make_response(
            buf,
            f'asset_card_{asset.inventory_number}.pdf',
        )


# ============================================================================
# 2. DepreciationReportPDFView  --  ОЗ-6 Відомість нарахування амортизації
# ============================================================================

class DepreciationReportPDFView(APIView):
    """
    ОЗ-6 — Вiдомiсть нарахування амортизацiї за мiсяць.

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
            f'Вiдомiсть нарахування амортизацiї (ОЗ-6)',
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
    Iнв-1 — Iнвентаризацiйний опис основних засобiв.

    GET /documents/inventory/<pk>/report/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        inventory = Inventory.objects.prefetch_related(
            'items__asset__group', 'commission_members',
        ).select_related('commission_head').get(pk=pk)

        items = inventory.items.select_related(
            'asset', 'asset__group',
        ).order_by('asset__inventory_number')

        styles = _get_styles()
        elements = []

        # -- Title --
        elements.append(Paragraph(
            'Iнвентаризацiйний опис основних засобiв (Iнв-1)',
            styles['UkrTitle'],
        ))
        elements.append(Spacer(1, 2 * mm))

        # -- Inventory header info --
        inv_rows = [
            ['Номер iнвентаризацiї:', inventory.number],
            ['Дата iнвентаризацiї:',
             inventory.date.strftime('%d.%m.%Y')],
            ['Наказ:', f'№{inventory.order_number} вiд '
                       f'{inventory.order_date.strftime("%d.%m.%Y")}'],
            ['Мiсце проведення:', inventory.location or '-'],
            ['Статус:', inventory.get_status_display()],
        ]
        if inventory.commission_head:
            inv_rows.append([
                'Голова комiсiї:',
                inventory.commission_head.get_full_name(),
            ])
        members = inventory.commission_members.all()
        if members.exists():
            member_names = ', '.join(m.get_full_name() for m in members)
            inv_rows.append(['Члени комiсiї:', member_names])

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

        # -- Signatures --
        elements.append(Spacer(1, 12 * mm))
        sig_rows = [['Голова комiсiї: ________________', '',
                     'Члени комiсiї: ________________']]
        sig_table = Table(sig_rows, colWidths=[65 * mm, 30 * mm, 65 * mm])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(sig_table)

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
    ОЗ-1 — Акт приймання-передачi основного засобу.

    GET /documents/receipt/<pk>/act/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        receipt = AssetReceipt.objects.select_related(
            'asset', 'asset__group', 'asset__responsible_person',
            'asset__organization', 'created_by',
        ).get(pk=pk)
        asset = receipt.asset

        styles = _get_styles()
        elements = []

        # -- Title --
        elements.append(Paragraph(
            'Акт приймання-передачi основного засобу (ОЗ-1)',
            styles['UkrTitle'],
        ))
        elements.append(Spacer(1, 2 * mm))

        if asset.organization:
            elements.append(Paragraph(
                f'Пiдприємство: {asset.organization}',
                styles['UkrCenter'],
            ))
            elements.append(Spacer(1, 2 * mm))

        # -- Document info --
        doc_rows = [
            ['Номер документа:', receipt.document_number],
            ['Дата документа:',
             receipt.document_date.strftime('%d.%m.%Y')],
            ['Тип надходження:', receipt.get_receipt_type_display()],
            ['Постачальник / джерело:', receipt.supplier or '-'],
        ]
        doc_table = Table(doc_rows, colWidths=[55 * mm, 115 * mm])
        doc_table.setStyle(_header_table_style())
        elements.append(doc_table)
        elements.append(Spacer(1, 5 * mm))

        # -- Asset info --
        elements.append(Paragraph(
            'Iнформацiя про основний засiб', styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 2 * mm))

        asset_rows = [
            ['Iнвентарний номер:', asset.inventory_number],
            ['Назва:', asset.name],
            ['Група ОЗ:', str(asset.group)],
            ['Рахунок облiку:', asset.group.account_number],
            ['Дата введення в експлуатацiю:',
             asset.commissioning_date.strftime('%d.%m.%Y')],
            ['Метод амортизацiї:',
             asset.get_depreciation_method_display()],
            ['Строк корисного використання (мiс.):',
             str(asset.useful_life_months)],
            ['Мiсцезнаходження:', asset.location or '-'],
            ['МВО:', (asset.responsible_person.get_full_name()
                      if asset.responsible_person else '-')],
        ]
        if asset.description:
            asset_rows.append(['Опис:', asset.description[:120]])
        asset_table = Table(asset_rows, colWidths=[55 * mm, 115 * mm])
        asset_table.setStyle(_header_table_style())
        elements.append(asset_table)
        elements.append(Spacer(1, 5 * mm))

        # -- Cost info --
        elements.append(Paragraph(
            'Вартiсть', styles['UkrSubtitle'],
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
        elements.append(Spacer(1, 15 * mm))
        sig_data = [
            ['Здав: ________________________', '',
             'Прийняв: ________________________'],
            ['', '', ''],
            ['М.П.', '', 'М.П.'],
        ]
        sig_table = Table(sig_data, colWidths=[70 * mm, 25 * mm, 70 * mm])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 3 * mm),
        ]))
        elements.append(sig_table)

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
    ОЗ-3 — Акт списання основного засобу.

    GET /documents/disposal/<pk>/act/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        disposal = AssetDisposal.objects.select_related(
            'asset', 'asset__group', 'asset__responsible_person',
            'asset__organization', 'created_by',
        ).get(pk=pk)
        asset = disposal.asset

        styles = _get_styles()
        elements = []

        # -- Title --
        elements.append(Paragraph(
            'Акт списання основного засобу (ОЗ-3)',
            styles['UkrTitle'],
        ))
        elements.append(Spacer(1, 2 * mm))

        if asset.organization:
            elements.append(Paragraph(
                f'Пiдприємство: {asset.organization}',
                styles['UkrCenter'],
            ))
            elements.append(Spacer(1, 2 * mm))

        # -- Document info --
        doc_rows = [
            ['Номер документа:', disposal.document_number],
            ['Дата документа:',
             disposal.document_date.strftime('%d.%m.%Y')],
            ['Тип вибуття:', disposal.get_disposal_type_display()],
        ]
        doc_table = Table(doc_rows, colWidths=[55 * mm, 115 * mm])
        doc_table.setStyle(_header_table_style())
        elements.append(doc_table)
        elements.append(Spacer(1, 5 * mm))

        # -- Asset info --
        elements.append(Paragraph(
            'Iнформацiя про основний засiб', styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 2 * mm))

        asset_rows = [
            ['Iнвентарний номер:', asset.inventory_number],
            ['Назва:', asset.name],
            ['Група ОЗ:', str(asset.group)],
            ['Рахунок облiку:', asset.group.account_number],
            ['Дата введення в експлуатацiю:',
             asset.commissioning_date.strftime('%d.%m.%Y')],
            ['Метод амортизацiї:',
             asset.get_depreciation_method_display()],
            ['Строк корисного використання (мiс.):',
             str(asset.useful_life_months)],
            ['МВО:', (asset.responsible_person.get_full_name()
                      if asset.responsible_person else '-')],
        ]
        asset_table = Table(asset_rows, colWidths=[55 * mm, 115 * mm])
        asset_table.setStyle(_header_table_style())
        elements.append(asset_table)
        elements.append(Spacer(1, 5 * mm))

        # -- Financial details of disposal --
        elements.append(Paragraph(
            'Фiнансовi дані на дату списання', styles['UkrSubtitle'],
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
        elements.append(Spacer(1, 5 * mm))

        # -- Reason --
        elements.append(Paragraph(
            'Причина вибуття', styles['UkrSubtitle'],
        ))
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(disposal.reason, styles['UkrNormal']))

        # -- Notes --
        if disposal.notes:
            elements.append(Spacer(1, 3 * mm))
            elements.append(Paragraph(
                f'Примiтки: {disposal.notes}', styles['UkrNormal'],
            ))

        # -- Signatures --
        elements.append(Spacer(1, 15 * mm))
        sig_data = [
            ['Голова комiсiї: ________________________', '',
             'Члени комiсiї: ________________________'],
            ['', '', ''],
            ['Гол. бухгалтер: ________________________', '',
             'Керiвник: ________________________'],
        ]
        sig_table = Table(sig_data, colWidths=[70 * mm, 25 * mm, 70 * mm])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 3 * mm),
        ]))
        elements.append(sig_table)

        # -- Build PDF --
        buf = io.BytesIO()
        _build_pdf(buf, elements)
        return _make_response(
            buf,
            f'disposal_act_{disposal.document_number}.pdf',
        )


# ============================================================================
# 6. AccountEntriesReportPDFView  --  Журнал проводок
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
