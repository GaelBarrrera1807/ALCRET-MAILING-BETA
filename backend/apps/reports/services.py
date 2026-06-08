import csv
import io
import logging
from datetime import datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Count, Avg
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

logger = logging.getLogger(__name__)


class ReportService:
    def generate_leads_report(self, filters=None):
        from apps.leads.models import Lead

        org_filter = {}
        if filters and filters.get('organization_id'):
            org_filter['organization_id'] = filters['organization_id']
        if filters and filters.get('status'):
            org_filter['status'] = filters['status']
        if filters and filters.get('priority'):
            org_filter['priority'] = filters['priority']

        leads = Lead.objects.filter(**org_filter).select_related('company').order_by('-score')

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        styles = getSampleStyleSheet()
        elements = []

        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Title'],
            fontSize=20, spaceAfter=30,
        )
        elements.append(Paragraph('Reporte de Leads - Prospección Industrial', title_style))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f'Generado: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 12))

        data = [['Empresa', 'Score', 'Prioridad', 'Estado', 'Sector', 'Teléfono', 'Email']]
        for lead in leads:
            data.append([
                lead.company.name[:40],
                str(lead.score),
                lead.priority,
                lead.status,
                lead.detected_sector[:30],
                lead.company.phone[:20],
                lead.company.email[:30],
            ])

        if len(data) > 1:
            table = Table(data, colWidths=[1.8*inch, 0.6*inch, 0.8*inch, 1*inch, 1.2*inch, 1*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph('No se encontraron leads.', styles['Normal']))

        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f'Total de leads: {leads.count()}', styles['Normal']))

        doc.build(elements)
        pdf_content = buffer.getvalue()
        buffer.close()

        return ContentFile(pdf_content)

    def generate_scoring_report(self, filters=None):
        from apps.companies.models import Company

        org_filter = {}
        if filters and filters.get('organization_id'):
            org_filter['organization_id'] = filters['organization_id']

        companies = Company.objects.filter(**org_filter).order_by('-score')

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        styles = getSampleStyleSheet()
        elements = []

        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Title'],
            fontSize=20, spaceAfter=30,
        )
        elements.append(Paragraph('Reporte de Scoring - Prospección Industrial', title_style))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f'Generado: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 12))

        avg_score = companies.aggregate(Avg('score'))['score__avg'] or 0
        elements.append(Paragraph(f'Score promedio: {avg_score:.1f}', styles['Normal']))
        elements.append(Paragraph(f'Total de empresas: {companies.count()}', styles['Normal']))
        elements.append(Spacer(1, 12))

        data = [['Empresa', 'Score', 'Sector', 'Estado', 'Ciudad']]
        for company in companies[:100]:
            data.append([
                company.name[:40],
                str(company.score),
                company.detected_sector[:25] or (company.sector.name[:25] if company.sector else ''),
                company.status,
                company.city[:20],
            ])

        if len(data) > 1:
            table = Table(data, colWidths=[2*inch, 0.6*inch, 1.2*inch, 0.8*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ]))
            elements.append(table)

        doc.build(elements)
        pdf_content = buffer.getvalue()
        buffer.close()

        return ContentFile(pdf_content)

    @staticmethod
    def _sanitize_csv_value(value: str) -> str:
        if value and value[0] in ('=', '+', '-', '@', '\t', '\r'):
            return "'" + value
        return value

    def _write_csv(self, headers, rows):
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        sanitized_rows = [
            [self._sanitize_csv_value(str(c) if c is not None else '') for c in row]
            for row in rows
        ]
        writer.writerows(sanitized_rows)
        csv_content = buffer.getvalue().encode('utf-8-sig')
        buffer.close()
        return ContentFile(csv_content)

    def generate_leads_csv(self, filters=None):
        from apps.leads.models import Lead

        org_filter = {}
        if filters and filters.get('organization_id'):
            org_filter['organization_id'] = filters['organization_id']
        if filters and filters.get('status'):
            org_filter['status'] = filters['status']
        if filters and filters.get('priority'):
            org_filter['priority'] = filters['priority']

        leads = Lead.objects.filter(**org_filter).select_related('company').order_by('-score')

        headers = ['Empresa', 'Score', 'Prioridad', 'Estado', 'Sector Detectado',
                    'Productos Recomendados', 'Teléfono', 'Email', 'Asignado A',
                    'Último Contacto', 'Seguimiento']
        rows = []
        for lead in leads:
            rows.append([
                lead.company.name,
                lead.score,
                lead.priority,
                lead.status,
                lead.detected_sector,
                lead.recommended_products,
                lead.company.phone,
                lead.company.email,
                lead.assigned_to.get_full_name() if lead.assigned_to else '',
                lead.last_contact.strftime('%Y-%m-%d') if lead.last_contact else '',
                lead.next_follow_up.strftime('%Y-%m-%d') if lead.next_follow_up else '',
            ])

        return self._write_csv(headers, rows)

    def generate_scoring_csv(self, filters=None):
        from apps.companies.models import Company

        org_filter = {}
        if filters and filters.get('organization_id'):
            org_filter['organization_id'] = filters['organization_id']

        companies = Company.objects.filter(**org_filter).order_by('-score')

        headers = ['Empresa', 'Score', 'Sector', 'Sector Detectado', 'Estado',
                    'Ciudad', 'Estado', 'Teléfono', 'Email', 'Es Cliente', 'Es Lead']
        rows = []
        for company in companies:
            rows.append([
                company.name,
                company.score,
                company.sector.name if company.sector else '',
                company.detected_sector,
                company.status,
                company.city,
                company.state,
                company.phone,
                company.email,
                'Sí' if company.is_client else 'No',
                'Sí' if company.is_lead else 'No',
            ])

        return self._write_csv(headers, rows)
