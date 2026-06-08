import logging
import time
from unidecode import unidecode

from apps.preprocessing.data import WEIGHTS
from apps.preprocessing.services.reader import FileReader
from apps.preprocessing.services.cleaner import DataCleaner
from apps.preprocessing.services.classifier import IndustryClassifier
from apps.preprocessing.services.scorer import RelevanceScorer
from apps.preprocessing.services.filter import LeadFilter
from apps.preprocessing.services.exporter import ExportService

logger = logging.getLogger(__name__)

TARGET_SECTORS = [
    'Transporte de carga general',
    'Construccion',
    'Agricola',
    'Alimentos',
    'Petrolera',
    'Petroquimica',
    'Refresquera',
    'Portuaria',
]

TARGET_SECTORS_NORM = {
    unidecode(s.lower().strip()) for s in TARGET_SECTORS
}

RELATED_SECTORS = [
    'Industrial',
    'Refacciones',
    'Talleres',
    'Material electrico',
    'Instalaciones y equipamiento',
    'Equipo especializado e industrial',
    'RPBI',
    'Mineria y materiales para construccion',
    'Mineria',
    'Manufactura industrial',
]

RELATED_SECTORS_NORM = {
    unidecode(s.lower().strip()) for s in RELATED_SECTORS
}


def _is_target_industry(industry_name):
    if not industry_name:
        return False
    norm = unidecode(industry_name.lower().strip())
    return norm in TARGET_SECTORS_NORM


def _is_related_industry(industry_name):
    if not industry_name:
        return False
    norm = unidecode(industry_name.lower().strip())
    return norm in RELATED_SECTORS_NORM


FIELD_KEYWORDS = {
    'name': [
        'nombre', 'razon social', 'denominacion',
        'denominacion', 'empresa', 'compania',
        'titular', 'cliente', 'proveedor', 'prospecto',
        'name', 'company', 'business',
    ],
    'description': [
        'descripcion', 'giro', 'actividad',
        'description', 'detalle', 'rubro', 'giro comercial',
    ],
}


def _match_column(col_name, keywords):
    col = unidecode(col_name.lower().strip())
    for kw in keywords:
        if kw in col:
            return True
    return False


def _find_value_in_columns(columns, row, field, default=''):
    keywords = FIELD_KEYWORDS.get(field, [])
    for col_name in columns:
        if _match_column(col_name, keywords):
            val = row.get(col_name, '')
            if val is not None and str(val).strip():
                return str(val).strip()
    return default


class PreprocessingResult:
    def __init__(self):
        self.total_records = 0
        self.relevant_records = 0
        self.filtered_records = 0
        self.records = []
        self.relevant = []
        self.discarded = []
        self.stats = {}
        self.cleaned_file_path = None
        self.processing_time = 0.0
        self.error = None
        self.original_filename = ''
        self.threshold = 30


class PreprocessingPipeline:
    def __init__(self, threshold=None, db_rules=None, use_ai_fallback=False):
        self.threshold = threshold or WEIGHTS.get('threshold_relevant', 30)
        self.use_ai_fallback = use_ai_fallback
        self.reader = FileReader()
        self.cleaner = DataCleaner()
        self.classifier = IndustryClassifier(db_rules=db_rules)
        self.scorer = RelevanceScorer(db_rules=db_rules)
        self.filter = LeadFilter(threshold=self.threshold)
        self.exporter = ExportService()
        
        # FIX #4: Log threshold configurado
        logger.info(f"Pipeline initialized - threshold: {self.threshold}, use_ai_fallback: {self.use_ai_fallback}")

    def process(self, filename, file_bytes, output_dir=None):
        start = time.time()
        result = PreprocessingResult()
        result.original_filename = filename
        result.threshold = self.threshold

        try:
            raw_rows = self.reader.read(filename, file_bytes)
            if not raw_rows:
                result.error = 'Archivo vacio o sin datos'
                result.processing_time = time.time() - start
                return result

            original_columns = list(raw_rows[0].keys()) if raw_rows else []

            cleaned_rows = self.cleaner.clean(raw_rows, original_columns)
            if not cleaned_rows:
                result.error = 'Sin registros validos despues de limpieza'
                result.processing_time = time.time() - start
                return result

            scored_records = []
            for row in cleaned_rows:
                name = _find_value_in_columns(original_columns, row, 'name')
                description = _find_value_in_columns(
                    original_columns, row, 'description'
                )
                row_text = f'{name} {description}'

                industry_results = self.classifier.classify(row_text)
                score_info = self.scorer.score(
                    name, description, industry_results
                )

                best_industry, best_score = self.classifier.get_best_industry(
                    row_text
                ) if industry_results else (None, 0)

                enriched = dict(row)
                enriched['_name'] = name
                enriched['_description'] = description
                enriched['_preprocess_score'] = score_info['score']
                enriched['_preprocess_priority'] = score_info['priority']
                enriched['_preprocess_industry'] = best_industry or ''
                enriched['_preprocess_industry_score'] = best_score
                enriched['_preprocess_excluded'] = score_info['is_excluded']
                enriched['_sector_note'] = ''
                enriched['score_info'] = score_info
                enriched['industry_info'] = industry_results
                
                # LOGGING TEMPORAL PARA DIAGNÓSTICO
                if any(keyword in name.upper() for keyword in ['CONSTRUCCION', 'TRANSPORTE', 'MAQUINARIA', 'DISTRIBUIDORA', 'EQUIPOS', 'MATERIAL', 'COMBUSTIBLE', 'AUTOMOTRIZ']):
                    logger.info(f"=== DEBUG EMPRESA POTENCIAL ===")
                    logger.info(f"Nombre: {name}")
                    logger.info(f"Descripción/Giro (primeros 250 chars): {description[:250]}")
                    logger.info(f"Score asignado: {score_info['score']}")
                    logger.info(f"Industria detectada: {best_industry}")
                    logger.info(f"Industria score: {best_score}")
                    logger.info(f"Priority: {score_info['priority']}")
                    logger.info(f"Is excluded: {score_info['is_excluded']}")
                    logger.info(f"=================================")
                
                scored_records.append(enriched)

            for rec in scored_records:
                industry = rec.get('_preprocess_industry', '')
                score_info = rec.get('score_info', {})
                is_excluded = score_info.get('is_excluded', False)
                if is_excluded:
                    rec['_sector_note'] = 'excluido'
                    continue

                current_score = score_info.get('score', 0)

                if _is_target_industry(industry):
                    rec['_sector_note'] = 'objetivo'
                elif _is_related_industry(industry):
                    rec['_sector_note'] = 'relacionado'
                    new_score = int(current_score * 0.7)
                    score_info['score'] = new_score
                    rec['_preprocess_score'] = new_score
                    if new_score <= 0:
                        score_info['priority'] = 'descartado'
                        rec['_preprocess_priority'] = 'descartado'
                elif current_score >= 5:
                    rec['_sector_note'] = 'sin_sector_definido'
                    new_score = int(current_score * 0.5)
                    score_info['score'] = new_score
                    rec['_preprocess_score'] = new_score
                    if new_score > 0:
                        score_info['priority'] = 'baja'
                        rec['_preprocess_priority'] = 'baja'
                    else:
                        score_info['priority'] = 'descartado'
                        rec['_preprocess_priority'] = 'descartado'
                else:
                    rec['_sector_note'] = 'descartado'
                    score_info['score'] = 0
                    rec['_preprocess_score'] = 0
                    score_info['priority'] = 'descartado'
                    rec['_preprocess_priority'] = 'descartado'

            relevant, discarded = self.filter.filter_records(scored_records)

            excluded_count = sum(1 for r in discarded if r.get('score_info', {}).get('is_excluded', False))
            zero_score_count = sum(1 for r in discarded if r.get('score_info', {}).get('score', 0) == 0 and not r.get('score_info', {}).get('is_excluded', False))
            borderline_count = len(discarded) - excluded_count - zero_score_count
            logger.info(
                f'Discarded breakdown: {excluded_count} excluidos, '
                f'{zero_score_count} con score=0 sin excluir, '
                f'{borderline_count} borderline (score 1-{self.threshold - 1})'
            )

            if self.use_ai_fallback and discarded:
                evaluate = [
                    r for r in discarded
                    if not r.get('score_info', {}).get('is_excluded', False)
                ]
                if evaluate:
                    try:
                        from apps.ai_engine.services import batch_classify_borderline
                        batch = [
                            {
                                'name': r.get('_name', ''),
                                'giro': r.get('_description', ''),
                                'index': i,
                                'score': r.get('_preprocess_score', 0),
                                'sector_note': r.get('_sector_note', ''),
                                'industria_detectada': r.get('_preprocess_industry', ''),
                            }
                            for i, r in enumerate(evaluate)
                        ]
                        ai_results = batch_classify_borderline(batch)
                        ai_confirmed = {
                            r['index'] for r in ai_results
                            if r.get('es_potencial')
                        }
                        rescued = []
                        for i, r in enumerate(evaluate):
                            if i in ai_confirmed:
                                r['_preprocess_score'] = max(
                                    r['_preprocess_score'], self.threshold
                                )
                                r['_preprocess_priority'] = 'baja'
                                r['score_info']['score'] = r['_preprocess_score']
                                rescued.append(r)
                        if rescued:
                            relevant.extend(rescued)
                            for r in rescued:
                                discarded.remove(r)
                            logger.info(
                                f'AI fallback rescued {len(rescued)} records'
                            )
                    except Exception as e:
                        logger.error(f'AI fallback error: {e}')

            stats = self.filter.summary_stats(scored_records)

            clean_records_for_export = []
            for rec in relevant:
                export_row = {
                    k: v for k, v in rec.items()
                    if not k.startswith('_') and k not in (
                        'score_info', 'industry_info'
                    )
                }
                export_row['score'] = rec.get('_preprocess_score', 0)
                export_row['prioridad'] = rec.get('_preprocess_priority', '')
                export_row['industria_detectada'] = rec.get(
                    '_preprocess_industry', ''
                )
                export_row['sector_note'] = rec.get('_sector_note', '')
                export_row['fleet_score'] = rec.get(
                    'score_info', {}
                ).get('fleet_score', 0)
                export_row['size_score'] = rec.get(
                    'score_info', {}
                ).get('size_score', 0)
                clean_records_for_export.append(export_row)

            cleaned_file_path = None
            if clean_records_for_export:
                cleaned_file_path = self.exporter.generate_cleaned_file(
                    clean_records_for_export, filename
                )

            result.total_records = len(scored_records)
            result.relevant_records = len(relevant)
            result.filtered_records = len(discarded)
            result.records = scored_records
            result.relevant = relevant
            result.discarded = discarded
            result.stats = stats
            result.cleaned_file_path = cleaned_file_path

        except Exception as e:
            logger.exception(f'Pipeline error: {e}')
            result.error = str(e)

        result.processing_time = round(time.time() - start, 3)
        logger.info(
            f'Pipeline completed: '
            f'{result.total_records} total, '
            f'{result.relevant_records} relevant, '
            f'{result.filtered_records} filtered, '
            f'in {result.processing_time}s'
        )
        return result
