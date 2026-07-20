import logging
import re

from celery import shared_task

logger = logging.getLogger(__name__)

STOP_WORDS = frozenset({
    'de', 'la', 'el', 'en', 'y', 'del', 'para', 'por', 'un', 'una',
    'con', 'sin', 'su', 'e', 'o', 'a', 'lo', 'los', 'las', 'al',
    'que', 'es', 'se', 'no', 'por', 'los', 'las',
})

WARNING_NO_EMAIL = (
    '⚠️ Requiere Prospección Telefónica Manual: '
    'Snov.io no detectó correos en LinkedIn. '
    'Usar teléfono de Google Maps'
)


def _extract_sector_keywords(sector):
    if not sector:
        return []
    tokens = re.sub(r'[^\w\sáéíóúüñÁÉÍÓÚÜÑ]', ' ', sector.lower()).split()
    return [t for t in tokens if len(t) > 2 and t not in STOP_WORDS]


def _find_campaign_by_sector(organization_id, sector, status='draft'):
    from apps.mailer.models import EmailCampaign

    base_qs = EmailCampaign.objects.filter(
        organization_id=organization_id,
        status=status,
        source_filter__in=('all', 'internal'),
    )
    for kw in _extract_sector_keywords(sector):
        match = base_qs.filter(name__icontains=kw).order_by('-created_at').first()
        if match:
            logger.info(
                'Campaña %s seleccionada por keyword "%s" del sector "%s"',
                match.id, kw, sector,
            )
            return match
    return base_qs.order_by('-created_at').first()


def _check_contact_has_email(contact_id, lead, company):
    if contact_id:
        try:
            contact = lead.contact
            if contact and contact.email:
                return True
        except Exception:
            pass
        try:
            from apps.core.models import CompanyContact
            contact = CompanyContact.objects.filter(id=contact_id).first()
            if contact and contact.email:
                return True
        except Exception:
            pass
    return bool(company.email)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def create_lead_from_classification(
    self, company_id: str, score: int = 0, priority: str = 'media',
    detected_sector: str = '', contact_id: str = None,
    organization_id: str = None, analysis_summary: str = '',
    reason: str = '', auto_enroll_campaign: bool = False,
):
    from apps.core.models import Company
    from apps.leads.models import Lead

    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        logger.error(f'Company {company_id} no encontrada para crear lead')
        return {'error': 'Company not found'}

    if hasattr(company, 'lead'):
        lead = company.lead
        lead.score = score
        lead.priority = priority
        lead.detected_sector = detected_sector or lead.detected_sector
        lead.analysis_summary = analysis_summary or lead.analysis_summary
        lead.reason = reason or lead.reason
        if contact_id:
            lead.contact_id = contact_id
        lead.save(update_fields=[
            'score', 'priority', 'detected_sector',
            'analysis_summary', 'reason', 'contact_id',
        ])
        logger.info(f'Lead actualizado para company={company_id}')
    else:
        lead = Lead.objects.create(
            company=company,
            contact_id=contact_id,
            organization_id=organization_id or company.organization_id,
            score=score,
            priority=priority,
            detected_sector=detected_sector,
            analysis_summary=analysis_summary,
            reason=reason,
            auto_created=True,
        )
        logger.info(f'Lead creado para company={company_id}')

    can_enroll = (
        auto_enroll_campaign
        and priority in ('alta', 'urgente')
        and score >= 60
    )

    if can_enroll and not _check_contact_has_email(contact_id, lead, company):
        if WARNING_NO_EMAIL not in (lead.analysis_summary or ''):
            lead.analysis_summary = (
                (lead.analysis_summary or '')
                + ('\n\n' if lead.analysis_summary else '')
                + WARNING_NO_EMAIL
            )
            lead.save(update_fields=['analysis_summary'])
            logger.info(
                'Lead %s: sin email — inyectada advertencia de prospección telefónica',
                lead.id,
            )
    elif can_enroll:
        _enroll_in_mailer_campaign(lead, company, contact_id)

    return {
        'lead_id': str(lead.id),
        'company_id': company_id,
        'score': score,
        'priority': priority,
        'auto_created': True,
    }


def _enroll_in_mailer_campaign(lead, company, contact_id=None):
    from apps.mailer.models import EmailRecipient

    if not lead.organization_id:
        return

    email = ''
    name = ''

    if contact_id:
        try:
            contact = lead.contact
            if contact:
                email = contact.email or ''
                name = contact.name or ''
        except Exception:
            pass

    if not email:
        email = company.email or ''

    if not name and contact_id:
        try:
            from apps.core.models import CompanyContact
            contact = CompanyContact.objects.filter(id=contact_id).first()
            if contact:
                name = contact.name or ''
                email = email or contact.email or ''
        except Exception:
            pass

    if not email:
        logger.info(f'Lead {lead.id}: sin email, no se puede enrolar en campaña')
        return

    recipient, created = EmailRecipient.objects.get_or_create(
        email=email,
        organization=lead.organization,
        defaults={
            'first_name': name.split()[0] if name else '',
            'company_name': company.name,
            'sector': lead.detected_sector or company.detected_sector or '',
            'source': 'lead_generation',
            'lead': lead,
        },
    )
    if not created:
        recipient.lead = lead
        recipient.is_active = True
        recipient.source = 'lead_generation'
        recipient.save(update_fields=['lead', 'is_active', 'source'])

    sector = lead.detected_sector or company.detected_sector or ''
    active_campaign = _find_campaign_by_sector(
        lead.organization_id, sector, status='draft',
    )

    if active_campaign and created:
        from apps.mailer.models import CampaignSend
        CampaignSend.objects.get_or_create(
            campaign=active_campaign,
            recipient=recipient,
        )
        active_campaign.total_recipients += 1
        active_campaign.save(update_fields=['total_recipients'])
        logger.info(
            'Lead %s: enrolado en campaña %s',
            lead.id, active_campaign.id,
        )
    elif active_campaign and not created:
        logger.info(
            'Lead %s: recipient ya existía, omitido enrolamiento duplicado en %s',
            lead.id, active_campaign.id,
        )


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def batch_create_leads_from_pipeline(
    self, company_ids: list, scores: list = None, priorities: list = None,
    sectors: list = None, organization_id: str = None,
    auto_enroll_campaign: bool = False,
):
    if scores is None:
        scores = [0] * len(company_ids)
    if priorities is None:
        priorities = ['media'] * len(company_ids)
    if sectors is None:
        sectors = [''] * len(company_ids)

    results = []
    for i, cid in enumerate(company_ids):
        result = create_lead_from_classification(
            cid,
            score=scores[i] if i < len(scores) else 0,
            priority=priorities[i] if i < len(priorities) else 'media',
            detected_sector=sectors[i] if i < len(sectors) else '',
            organization_id=organization_id,
            auto_enroll_campaign=auto_enroll_campaign,
        )
        results.append(result)

    created = sum(1 for r in results if r.get('lead_id'))
    logger.info(f'Batch create leads: {created} leads procesados de {len(company_ids)}')
    return {'processed': len(company_ids), 'created': created}
