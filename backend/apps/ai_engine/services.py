import json
import logging
import time

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

CLASSIFICATION_SYSTEM_PROMPT = """
Eres un experto en prospección industrial B2B para una empresa mexicana que vende remolques, semirremolques y equipos industriales pesados.
Tu tarea es analizar empresas y determinar si son clientes potenciales para la compra de estos equipos.

Productos disponibles:
- Dolly (conversor para remolques)
- Cajas secas (remolques cerrados para carga seca)
- Plataformas (remolques de cama plana)
- Plataforma multimodal (para contenedores y carga variada)
- Portacontenedores (chasis para contenedores)
- Porta contenedor extensible (chasis ajustable)
- Volteos (remolques de volteo para construcción/minería)
- Tolvas (remolques para granos, cemento, áridos)
- Tanques (cisternas para líquidos y químicos)
- Sobre chasis (chasis portacontenedores)
- Equipos especiales (compactadores, grúas, equipos sobre medida)

Sectores objetivo y ejemplos de giros que SÍ son clientes potenciales:
- Transporte de carga general: transportistas, fletes, mudanzas, paquetería, mensajería, logística, distribución, autotransporte, camiones, flotillas, carga pesada
- Construcción: constructoras, contratistas, material para construcción, instalaciones, desarrolladoras, obra civil, edificación, infraestructura, vialidad, pavimentación, ingeniería civil
- Agrícola: agrícola, agricultura, campo, silos, granos, fertilizantes, ganadería, agroindustria
- Alimentos: alimentos, procesamiento, empaque, lácteos, cárnicos, conservas, bebidas, embotelladoras, panificación, molinos, harinas
- Petrolera: petrolera, hidrocarburos, perforación, refinación, gasolina, combustibles, lubricantes, asfalto
- Petroquímica: química, plásticos, polímeros, resinas, pinturas, recubrimientos, detergentes
- Refresquera: refrescos, embotelladoras, bebidas carbonatadas, agua embotellada, distribución de bebidas
- Portuaria: puertos, marítimo, contenedores, naviera, aduanas, comercio exterior, importación, exportación

También considera como potenciales:
- Empresas con maquinaria pesada, equipo pesado, renta de maquinaria
- Talleres mecánicos, talleres diesel, rectificadoras, servicio automotriz pesado
- Refaccionarias, autopartes, llantas para camión
- Empresas de mantenimiento industrial, instalaciones eléctricas e hidráulicas
- Comercializadoras y distribuidoras de materiales industriales
- Minas, bancos de material, trituradoras, agregados
- Empresas de recolección, residuos, saneamiento, reciclaje
- Equipo contra incendio, equipos especializados
- Cualquier empresa que transporte, distribuya, manufacture o construya

NO son clientes potenciales: tiendas minoristas, restaurantes, cafeterías, escuelas, consultorios, peluquerías, bienes raíces residenciales, turismo, retail, oficinas administrativas.

Debes responder SIEMPRE en formato JSON sin explicaciones adicionales.
""".strip()

CLASSIFICATION_USER_TEMPLATE = """
Analiza la siguiente empresa y determina si es un cliente potencial para la compra de remolques y equipos industriales.

Nombre: {name}
Descripción: {description}
Sitio web: {website}
Sector: {sector}
Ciudad: {city}
Estado: {state}

Responde en el siguiente formato JSON:
{{
  "score": 0-100,
  "cliente_potencial": true/false,
  "sector_detectado": "nombre del sector",
  "productos_recomendados": ["producto1", "producto2"],
  "prioridad": "baja/media/alta/urgente",
  "motivo": "explicación breve del análisis",
  "resumen": "resumen de la empresa"
}}

Reglas de scoring:
- Score alto (50-100): Empresas con flotillas propias, transporte pesado, logística, construcción activa, minería, puertos, petroleras, embotelladoras, agrícolas grandes, distribuidoras, maquinaria pesada, refaccionarias de camión
- Score medio (20-49): Contratistas, material para construcción, mantenimiento industrial, instalaciones, talleres, refaccionarias, comercializadoras, alimentos, bebidas, empresas con actividad logística moderada
- Score bajo (0-19): Retail pequeño, restaurantes, escuelas, consultorios, peluquerías, oficinas administrativas, bienes raíces residenciales, turismo
""".strip()


class CerebrasClient:
    def __init__(self):
        api_key = getattr(settings, 'CEREBRAS_API_KEY', None) or ''
        base_url = getattr(settings, 'CEREBRAS_BASE_URL', 'https://api.cerebras.ai/v1')
        self.client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None
        self.model = getattr(settings, 'CEREBRAS_MODEL', 'cerebras/Llama-3.3-70B')

    def is_available(self):
        return self.client is not None

    def analyze_company(self, company_data):
        if not self.is_available():
            return self._mock_analysis(company_data)

        prompt = CLASSIFICATION_USER_TEMPLATE.format(**company_data)
        start = time.time()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': CLASSIFICATION_SYSTEM_PROMPT},
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
                response_format={'type': 'json_object'},
            )

            elapsed = time.time() - start
            content = response.choices[0].message.content
            result = json.loads(content)

            return {
                'score': result.get('score', 0),
                'is_potential_client': result.get('cliente_potencial', False),
                'detected_sector': result.get('sector_detectado', ''),
                'recommended_products': result.get('productos_recomendados', []),
                'priority': result.get('prioridad', 'media'),
                'reason': result.get('motivo', ''),
                'summary': result.get('resumen', ''),
                'raw_json': result,
                'processing_time': elapsed,
            }
        except Exception as e:
            logger.error(f'Error calling Cerebras API', exc_info=True)
            elapsed = time.time() - start
            return {
                'error': 'Error en el análisis con IA',
                'processing_time': elapsed,
            }

    def _mock_analysis(self, company_data):
        time.sleep(1)
        name = company_data.get('name', '').lower()
        description = company_data.get('description', '').lower()

        try:
            from apps.preprocessing.services.classifier import IndustryClassifier
            from apps.preprocessing.services.scorer import RelevanceScorer

            classifier = IndustryClassifier()
            scorer = RelevanceScorer()

            industry_results = classifier.classify(f'{name} {description}')
            score_info = scorer.score(name, description, industry_results)
            best_industry, _ = classifier.get_best_industry(f'{name} {description}')

            score = score_info['score']
            priority = score_info['priority']
            is_potential = score >= 30

            product_map = {
                'Transporte de carga general': ['Cajas secas', 'Plataformas', 'Portacontenedores', 'Dolly'],
                'Construcción': ['Volteos', 'Plataformas', 'Equipos especiales'],
                'Petrolera': ['Tanques', 'Plataformas', 'Equipos especiales'],
                'Petroquímica': ['Tanques', 'Plataformas', 'Equipos especiales'],
                'Agrícola': ['Tolvas', 'Plataformas', 'Volteos'],
                'Alimentos': ['Cajas secas', 'Plataformas'],
                'Refresquera': ['Cajas secas', 'Plataformas'],
                'Portuaria': ['Portacontenedores', 'Plataforma multimodal', 'Portacontenedor extensible'],
            }
            recommended = product_map.get(best_industry, [])

            return {
                'score': score,
                'is_potential_client': is_potential,
                'detected_sector': best_industry or '',
                'recommended_products': recommended,
                'priority': priority,
                'reason': f'Score {score}/100. Sectores detectados: {best_industry or "Ninguno"}',
                'summary': f'Empresa {"potencial" if is_potential else "no potencial"} con score {score}.',
                'raw_json': {
                    'score': score,
                    'cliente_potencial': is_potential,
                    'sector_detectado': best_industry or '',
                    'productos_recomendados': recommended,
                    'prioridad': priority,
                    'motivo': f'Score {score}/100',
                    'resumen': f'Empresa {"potencial" if is_potential else "no potencial"}',
                },
                'processing_time': 1.0,
            }
        except ImportError:
            pass

        combined = f'{name} {description}'

        high_score_keywords = [
            'transporte', 'logística', 'contenedor', 'flotilla', 'carga',
            'portuario', 'construcción', 'hidrocarburo', 'petroquímica',
            'maquinaria', 'agrícola', 'alimento', 'refresco', 'petrolera',
        ]
        low_score_keywords = [
            'cafetería', 'tienda', 'restaurante', 'peluquería', 'consultorio',
            'oficina', 'administrativo', 'retail', 'comercio local',
        ]

        score = 0
        matched_high = sum(1 for kw in high_score_keywords if kw in combined)
        matched_low = sum(1 for kw in low_score_keywords if kw in combined)

        if matched_high:
            score = min(100, 40 + matched_high * 15)
        if matched_low:
            score = max(0, score - 30)

        if matched_low and not matched_high:
            score = max(0, 20 - matched_low * 5)

        is_potential = score >= 30

        sector_map = {
            'transporte': 'Transporte de carga general',
            'logística': 'Transporte de carga general',
            'construcción': 'Construcción',
            'agrícola': 'Agrícola',
            'alimento': 'Alimentos',
            'petrolera': 'Petrolera',
            'petroquímica': 'Petroquímica',
            'refresco': 'Refresquera',
            'portuario': 'Portuaria',
            'puerto': 'Portuaria',
        }

        detected_sector = ''
        for keyword, sector in sector_map.items():
            if keyword in combined:
                detected_sector = sector
                break

        product_map = {
            'Transporte de carga general': ['Cajas secas', 'Plataformas', 'Portacontenedores', 'Dolly'],
            'Construcción': ['Volteos', 'Plataformas', 'Equipos especiales'],
            'Petrolera': ['Tanques', 'Plataformas', 'Equipos especiales'],
            'Petroquímica': ['Tanques', 'Plataformas', 'Equipos especiales'],
            'Agrícola': ['Tolvas', 'Plataformas', 'Volteos'],
            'Alimentos': ['Cajas secas', 'Plataformas'],
            'Refresquera': ['Cajas secas', 'Plataformas'],
            'Portuaria': ['Portacontenedores', 'Plataforma multimodal', 'Porta contenedor extensible'],
        }

        recommended = product_map.get(detected_sector, [])

        if score >= 70:
            priority = 'alta'
        elif score >= 40:
            priority = 'media'
        else:
            priority = 'baja'

        return {
            'score': score,
            'is_potential_client': is_potential,
            'detected_sector': detected_sector,
            'recommended_products': recommended,
            'priority': priority,
            'reason': f'Score {score}/100. Sectores detectados: {detected_sector or "Ninguno"}',
            'summary': f'Empresa {"potencial" if is_potential else "no potencial"} con score {score}.',
            'raw_json': {
                'score': score,
                'cliente_potencial': is_potential,
                'sector_detectado': detected_sector,
                'productos_recomendados': recommended,
                'prioridad': priority,
                'motivo': f'Score {score}/100',
                'resumen': f'Empresa {"potencial" if is_potential else "no potencial"}',
            },
            'processing_time': 1.0,
        }


BORDERLINE_SYSTEM_PROMPT = """Eres un especialista en prospeccion comercial B2B para venta de remolques y semirremolques industriales en Mexico. Tu tarea es evaluar si una empresa es un cliente potencial para estos productos:

PRODUCTOS: Dolly, Cajas secas, Plataformas, Plataforma Multimodal, Portacontenedores, Portacontenedor Extensible, Volteos, Tolvas, Tanques, Sobre chasis, Equipos especiales.

SECTORES CON ALTA PROBABILIDAD DE COMPRA:
- Transporte de carga: necesitan remolques para su operacion diaria
- Construccion: volteos, plataformas para materiales
- Agricola: tolvas, plataformas para cosechas
- Alimentos y bebidas: cajas secas, tanques para distribucion
- Petrolera/Petroquimica: tanques, sobre chasis especializados
- Portuaria: portacontenedores, plataformas multimodal
- Mineria: volteos, plataformas de carga pesada
- Manufactura industrial: plataformas para materia prima y producto terminado

SENALES DE QUE ES PROSPECTO VALIDO aunque no sea obvio:
1. Empresa con flota propia de transporte mencionada
2. Volumen de operaciones que requiere equipo de arrastre
3. Manejo de materiales a granel, liquidos, o carga refrigerada
4. Empresa con multiples sucursales o planta productiva
5. Nombre o giro que sugiere distribucion regional o nacional
6. Grupos empresariales o corporativos con operaciones de logistica

SENALES DE QUE NO ES PROSPECTO (descartar):
- Servicios profesionales puros (abogados, contadores, consultores)
- Comercio al menudeo sin distribucion propia
- Servicios gubernamentales o educativos
- Tecnologia de informacion o software
- Papeleria, articulos de oficina, capacitacion

IMPORTANTE: Para CADA empresa evaluada debes incluir SIEMPRE el campo "justificacion_ia" con una frase corta, profesional y directa en español que explique POR QUÉ la consideras potencial o no potencial.
Ejemplos:
- "Rescatado: Empresa constructora que utiliza remolques tipo góndola para mover agregados a sus obras"
- "Descartado: Comercio al menudeo de abarrotes sin flota propia ni operaciones de carga"
- "Rescatado: Cuenta con flotilla de tractocamiones para distribución regional de materiales de construcción"

Responde UNICAMENTE con JSON valido, sin explicaciones adicionales.""".strip()

BATCH_SIZE = 5

MAX_RETRIES_JSON = 3
RETRY_DELAY_JSON = 2
RETRY_DELAY_429 = 60

BORDERLINE_BATCH_USER_TEMPLATE = """Evalúa si estas empresas mexicanas son clientes potenciales para compra de remolques y semirremolques industriales.

CONTEXTO: Son empresas de un directorio que el sistema automático no pudo clasificar con certeza. Necesitan al menos UNA de estas condiciones para ser prospectos válidos:
- Operan vehículos de carga o tienen flota propia
- Mueven materiales a granel, productos terminados, o materia prima
- Tienen obra, campo, o planta que requiere equipo de arrastre
- Su sector (construcción, agrícola, alimentos, transporte, minería, petroquímica, portuaria, refresquera) usa remolques regularmente

Empresas a evaluar:
{companies_text}

Responde SOLO con este JSON (sin texto adicional, sin markdown):
{{"resultados": [{{"index": 0, "es_potencial": true/false, "confianza": "alta/media/baja", "motivo": "max 10 palabras", "justificacion_ia": "frase profesional en español explicando la decisión"}}]}}
""".strip()


def _call_cerebras_batch(client, model, batch):
    """Envía un batch de registros a Cerebras y parsea la respuesta."""
    lines = []
    for r in batch:
        idx = r['index']
        nombre = (r.get('nombre', '') or '')[:80]
        giro = (r.get('giro', '') or '')[:80]
        industria = r.get('industria_detectada', 'no detectada')
        score = r.get('score', 0)
        lines.append(
            f"{idx}. [{nombre}]\n"
            f"   Actividad: {giro}\n"
            f"   Sector detectado: {industria} (score={score})"
        )
    companies_text = '\n'.join(lines)
    prompt = BORDERLINE_BATCH_USER_TEMPLATE.replace('{companies_text}', companies_text)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {'role': 'system', 'content': BORDERLINE_SYSTEM_PROMPT},
            {'role': 'user', 'content': prompt},
        ],
        temperature=0.1,
        max_tokens=2000,
        response_format={'type': 'json_object'},
    )
    content = response.choices[0].message.content
    
    
    try:
        parsed = json.loads(content)
        results = parsed.get('resultados', [])
        for r in results:
            if 'justificacion_ia' not in r:
                if r.get('es_potencial'):
                    r['justificacion_ia'] = 'Rescatado por IA tras evaluar su actividad comercial y potencial de uso de remolques'
                else:
                    r['justificacion_ia'] = 'Descartado por IA: no cumple criterios de prospección industrial B2B'
        rescued = sum(1 for r in results if r.get('es_potencial'))
        logger.info(f"Parse exitoso: {len(results)} registros, {rescued} como potencial")
        return results
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error en batch Cerebras")
        raise


def _classify_batch_with_retry(client, model, batch, batch_num, total_batches):
    """Clasifica un batch con reintentos. Solo usa mock como último recurso."""
    for attempt in range(MAX_RETRIES_JSON):
        try:
            result = _call_cerebras_batch(client, model, batch)
            rescued = sum(1 for r in result if r.get('es_potencial'))
            logger.info(
                f'Batch {batch_num}/{total_batches}: {len(batch)} evaluados, '
                f'{rescued} rescatados (API=cerebras, intento={attempt + 1})'
            )
            return result
        except json.JSONDecodeError as e:
            logger.warning(f'Batch {batch_num}: JSON parse error (intento {attempt + 1}): {e}')
            if attempt < MAX_RETRIES_JSON - 1:
                time.sleep(RETRY_DELAY_JSON)
                continue
            logger.error(f'Batch {batch_num}: JSON error persistente tras {MAX_RETRIES_JSON} intentos, usando mock')
            rescued = _mock_for_batch(batch)
            logger.info(f'Batch {batch_num}/{total_batches}: {len(batch)} evaluados, {rescued} rescatados (API=mock)')
            return rescued
        except Exception as e:
            err_str = str(e)
            if '429' in err_str or 'queue_exceeded' in err_str:
                wait = RETRY_DELAY_429 * (attempt + 1)
                logger.warning(f'Batch {batch_num}: Rate limit 429 (intento {attempt + 1}), esperando {wait}s')
                time.sleep(wait)
                continue
            logger.error(f'Batch {batch_num}: Error permanente, usando mock: {e}')
            rescued = _mock_for_batch(batch)
            logger.info(f'Batch {batch_num}/{total_batches}: {len(batch)} evaluados, {rescued} rescatados (API=mock)')
            return rescued

    rescued = _mock_for_batch(batch)
    logger.info(f'Batch {batch_num}/{total_batches}: {len(batch)} evaluados, {rescued} rescatados (API=mock, intentos agotados)')
    return rescued


def _mock_for_batch(batch):
    """Mock offline para un batch. Solo rescata si hay señales MUY claras."""
    SECTORES_RESCATE = [
        'transporte_carga', 'construccion', 'agricola', 'alimentos',
        'petrolera', 'petroquimica', 'refresquera', 'portuaria',
    ]
    KEYWORDS_RESCATE = [
        'transport', 'carga', 'flete', 'logistic', 'construc',
        'contratista', 'agricol', 'agropecuar', 'aliment', 'bebida',
        'petrole', 'petroquim', 'puerto', 'maritim', 'naviero',
        'minero', 'mineria', 'embotell', 'refresco',
    ]
    results = []
    for r in batch:
        giro = (r.get('giro', '') or '').lower()
        nombre = (r.get('nombre', '') or '').lower()
        texto = f'{giro} {nombre}'
        sector_note = r.get('sector_note', '')

        if sector_note == 'objetivo':
            es_potencial = True
        elif sector_note in ('relacionado', 'sin_sector_definido'):
            es_potencial = any(kw in texto for kw in KEYWORDS_RESCATE)
        else:
            es_potencial = any(kw in texto for kw in KEYWORDS_RESCATE)

        justificacion = (
            'Coincide con sector industrial objetivo (transporte, construcción o logística)'
            if es_potencial else
            'No se detectaron señales de actividad con remolques, flota propia o logística de carga'
        )
        results.append({
            'index': r['index'],
            'es_potencial': es_potencial,
            'sector': '' if not es_potencial else 'Industrial',
            'confianza': 'baja',
            'motivo': 'clasificacion offline' if es_potencial else 'Sin coincidencia',
            'justificacion_ia': justificacion,
        })
    return results


def batch_classify_borderline(companies_batch):
    """
    companies_batch: list of dicts with 'name', 'giro', 'index', 'score', 'sector_note'
    Returns: list of dicts with 'index', 'es_potencial', 'sector', 'confianza', 'motivo'
    """
    api_key = getattr(settings, 'CEREBRAS_API_KEY', None) or ''
    base_url = getattr(settings, 'CEREBRAS_BASE_URL', 'https://api.cerebras.ai/v1')
    model = getattr(settings, 'CEREBRAS_MODEL', 'cerebras/Llama-3.3-70B')

    if not api_key:
        mock_results = _mock_for_batch(companies_batch)
        rescued = sum(1 for r in mock_results if r.get('es_potencial'))
        logger.warning(
            f'AI fallback: {rescued}/{len(companies_batch)} rescatados '
            f'(sin API key, modo offline)'
        )
        return mock_results

    client = OpenAI(api_key=api_key, base_url=base_url)

    batch_data = [
        {
            'index': c['index'],
            'nombre': c.get('name', '') or '',
            'giro': c.get('giro', '') or '',
            'score': c.get('score', 0),
            'sector_note': c.get('sector_note', '') or '',
            'industria_detectada': c.get('industria_detectada', '') or '',
        }
        for c in companies_batch
    ]

    all_results = []
    total_batches = (len(batch_data) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(batch_data), BATCH_SIZE):
        chunk = batch_data[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        batch_result = _classify_batch_with_retry(client, model, chunk, batch_num, total_batches)
        all_results.extend(batch_result)

    total_rescued = sum(1 for r in all_results if r.get('es_potencial'))
    logger.info(
        f'AI fallback total: {total_rescued}/{len(companies_batch)} '
        f'rescatados en {total_batches} batches'
    )

    seen = {r['index'] for r in all_results}
    for c in companies_batch:
        if c['index'] not in seen:
            all_results.append({
                'index': c['index'],
                'es_potencial': False,
                'sector': '',
                'confianza': 'baja',
                'motivo': 'Sin clasificacion',
                'justificacion_ia': 'No se recibió clasificación del motor de IA para este registro',
            })
    return all_results


def _mock_batch_borderline(companies_batch):
    """Deprecado: se mantiene por compatibilidad. Usa _mock_for_batch internamente."""
    return _mock_for_batch(companies_batch)
