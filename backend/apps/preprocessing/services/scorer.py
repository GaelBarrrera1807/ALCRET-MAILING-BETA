import logging
import re

from apps.preprocessing.data import EXCLUDE_KEYWORDS, WEIGHTS
from apps.preprocessing.data.products import FINANCIAL_KEYWORDS, PRODUCT_KEYWORDS
from apps.preprocessing.services.cleaner import DataCleaner, keyword_match

logger = logging.getLogger(__name__)


FLEET_INDICATORS_HIGH = [
    'flota', 'flotilla', 'unidades propias', 'tracto', 'tractocamion',
    'semirremolque', 'remolque', 'tractor', 'camion de carga',
    'vehiculos de carga', 'parque vehicular', 'unidades de transporte',
]

FLEET_INDICATORS_MEDIUM = [
    'camion', 'camiones', 'vehiculo', 'vehiculos de trabajo',
    'equipo de transporte', 'unidades', 'transporte propio',
]

SIZE_INDICATORS = [
    'grupo', 'corporativo', 'holding', 'nacional', 'internacional',
    's.a.', 's.a.p.i.', 's.a. de c.v.', 's. de r.l.', 'sociedad anonima',
    'empresa', 'compania', 'cia', 'industrias', 'servicios integrales',
]


class RelevanceScorer:
    def __init__(self, db_rules=None):
        self.exclude_keywords = list(EXCLUDE_KEYWORDS)
        self.weights = WEIGHTS
        self.db_rules = db_rules or []

    def score(self, name, description='', industry_results=None):
        combined = DataCleaner.normalize_company_text(name, description)
        if self._is_excluded(combined):
            return {
                'score': 0,
                'priority': 'descartado',
                'is_excluded': True,
                'industry_score': 0,
                'fleet_score': 0,
                'size_score': 0,
                'bonus_score': 0,
                'bonus_comercial': 0,
                'lead_intent_type': '',
                'details': 'Contiene palabras de exclusion',
            }
        if industry_results is None:
            from apps.preprocessing.services.classifier import IndustryClassifier
            industry_results = IndustryClassifier().classify(f'{name} {description}')
        desc_only = DataCleaner.normalize_company_text('', description)
        industry_score = self._calc_industry_score(industry_results)
        fleet_score = self._calc_fleet_score(desc_only)
        size_score = self._calc_company_size_score(combined)
        bonus_score = self._calc_bonus(combined)
        description_bonus = self._calc_description_bonus(description)
        bonus_comercial, lead_intent_type = self._calc_commercial_intent(
            combined, industry_results
        )
        raw_score = (industry_score + fleet_score + size_score
                      + bonus_score + description_bonus + bonus_comercial)
        final_score = min(self.weights['score_max'], max(0, raw_score))
        priority = self._determine_priority(final_score)
        return {
            'score': final_score,
            'priority': priority,
            'is_excluded': False,
            'industry_score': industry_score,
            'fleet_score': fleet_score,
            'size_score': size_score,
            'bonus_score': bonus_score + description_bonus,
            'bonus_comercial': bonus_comercial,
            'lead_intent_type': lead_intent_type,
            'details': {
                'industry_score': industry_score,
                'fleet_score': fleet_score,
                'size_score': size_score,
                'bonus_score': bonus_score,
                'description_bonus': description_bonus,
                'bonus_comercial': bonus_comercial,
                'raw_score': raw_score,
            },
        }

    def _is_excluded(self, text):
        for kw in self.exclude_keywords:
            if ' ' in kw:
                if kw in text:
                    logger.debug(f'Exclusion match: keyword="{kw}" in text (first 80): {text[:80]}')
                    return True
            else:
                if re.search(rf'\b{re.escape(kw)}\b', text):
                    logger.debug(f'Exclusion match: keyword="{kw}" in text (first 80): {text[:80]}')
                    return True
        for rule in self.db_rules:
            if rule.get('rule_type') != 'exclusion':
                continue
            for kw in rule.get('keywords', []):
                kw_lower = kw.lower()
                if ' ' in kw_lower:
                    if kw_lower in text:
                        return True
                else:
                    if re.search(rf'\b{re.escape(kw_lower)}\b', text):
                        return True
        return False

    def _calc_industry_score(self, industry_results):
        if not industry_results:
            return 0
        total = 0
        for key, info in industry_results.items():
            weight = info.get('weight', 5)
            score = info.get('score', 0)
            total += score * weight
        return min(int(total), 40)

    def _calc_fleet_score(self, text):
        score = 0
        matches_high = 0
        for kw in FLEET_INDICATORS_HIGH:
            if keyword_match(text, kw):
                matches_high += 1
                if matches_high >= 2:
                    break
        score += matches_high * self.weights['bonus_fleet_high']
        for kw in FLEET_INDICATORS_MEDIUM:
            if keyword_match(text, kw):
                score += self.weights['bonus_fleet_medium']
                break
        return score

    def _calc_company_size_score(self, text):
        for kw in SIZE_INDICATORS:
            if keyword_match(text, kw):
                return self.weights['bonus_size']
        return 0

    def _calc_bonus(self, text):
        complementary = [
            'camion', 'remolque', 'semirremolque', 'tractor camion',
            'pesados', 'pesada', 'vehiculo pesado', 'equipo pesado',
            'maquinaria pesada', 'flota', 'unidades', 'partes',
            'construccion', 'constructora', 'obra', 'mineria', 'industrial',
            'fabrica', 'material', 'materiales', 'equipo',
            'instalacion', 'refaccion', 'refacciones',
            'reparacion', 'transporte',
            'carga', 'logistica',
        ]
        score = 0
        for kw in complementary:
            if keyword_match(text, kw):
                score += self.weights['bonus_complementary']
                break
        return score

    def _calc_description_bonus(self, description):
        if not description or not isinstance(description, str):
            return 0
        desc_text = description.lower().strip()
        min_chars = self.weights.get('description_length_bonus', {}).get('min_chars', 50)
        points = self.weights.get('description_length_bonus', {}).get('points', 5)
        if len(desc_text) >= min_chars:
            return points
        return 0

    def _calc_commercial_intent(self, combined, industry_results):
        has_financial = any(
            keyword_match(combined, kw) for kw in FINANCIAL_KEYWORDS
        )
        is_transporte = any(
            key == 'transporte_carga' for key in (industry_results or {})
        )
        if has_financial:
            return self.weights.get('bonus_commercial', 15), 'SQL'
        if is_transporte:
            return 0, 'MQL'
        return 0, ''

    def _determine_priority(self, score):
        threshold_high = self.weights.get('threshold_high_priority', 60)
        threshold_relevant = self.weights.get('threshold_relevant', 30)
        if score >= threshold_high:
            return 'alta'
        if score >= threshold_relevant:
            return 'media'
        if score > 0:
            return 'baja'
        return 'descartado'
