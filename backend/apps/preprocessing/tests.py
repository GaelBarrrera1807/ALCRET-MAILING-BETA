import base64
import csv
import io
import json
import os
import tempfile

from django.test import TestCase

from apps.preprocessing.services.reader import FileReader
from apps.preprocessing.services.cleaner import DataCleaner
from apps.preprocessing.services.classifier import IndustryClassifier
from apps.preprocessing.services.scorer import RelevanceScorer
from apps.preprocessing.services.filter import LeadFilter
from apps.preprocessing.services.exporter import ExportService
from apps.preprocessing.services.pipeline import PreprocessingPipeline


class TestFileReader(TestCase):
    def setUp(self):
        self.reader = FileReader()

    def test_read_csv(self):
        content = b'nombre,giro,ciudad\nEmpresa A,Transporte,CDMX\nEmpresa B,Construccion,MTY\n'
        rows = self.reader.read('test.csv', content)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['nombre'], 'Empresa A')

    def test_read_csv_latin1(self):
        content = 'nombre,giro\nEmpresa Á,Transporte\n'.encode('latin-1')
        rows = self.reader.read('test.csv', content)
        self.assertEqual(len(rows), 1)

    def test_read_xlsx_simulated_as_csv(self):
        content = b'nombre,giro\nTest,Logistica\n'
        with self.assertRaises(ValueError):
            self.reader.read('test.txt', content)

    def test_empty_csv(self):
        content = b''
        rows = self.reader.read('test.csv', content)
        self.assertEqual(len(rows), 0)


class TestDataCleaner(TestCase):
    def setUp(self):
        self.cleaner = DataCleaner()

    def test_remove_empty_rows(self):
        rows = [
            {'nombre': 'Empresa A', 'giro': 'Transporte'},
            {'nombre': '', 'giro': ''},
            {'nombre': 'Empresa B', 'giro': 'Construccion'},
        ]
        columns = ['nombre', 'giro']
        cleaned = self.cleaner.clean(rows, columns)
        self.assertEqual(len(cleaned), 2)

    def test_remove_duplicates(self):
        rows = [
            {'nombre': 'Empresa A', 'giro': 'Transporte'},
            {'nombre': 'Empresa A', 'giro': 'Transporte'},
        ]
        columns = ['nombre', 'giro']
        cleaned = self.cleaner.clean(rows, columns)
        self.assertEqual(len(cleaned), 1)

    def test_normalize_text(self):
        result = self.cleaner._normalize_text('  Empresa de  Transporte  ')
        self.assertEqual(result, 'empresa de transporte')

    def test_null_values(self):
        rows = [
            {'nombre': 'Empresa A', 'giro': None},
        ]
        columns = ['nombre', 'giro']
        cleaned = self.cleaner.clean(rows, columns)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]['giro'], '')


class TestIndustryClassifier(TestCase):
    def setUp(self):
        self.classifier = IndustryClassifier()

    def test_detect_transporte(self):
        text = 'Empresa de transporte de carga y logistica'
        results = self.classifier.classify(text)
        self.assertIn('transporte_carga', results)
        self.assertGreater(results['transporte_carga']['score'], 0)

    def test_detect_construccion(self):
        text = 'Constructora dedicada a obras de infraestructura civil'
        results = self.classifier.classify(text)
        self.assertIn('construccion', results)

    def test_no_match(self):
        text = 'Servicios de consultoria fiscal y contable'
        results = self.classifier.classify(text)
        self.assertEqual(len(results), 0)

    def test_best_industry(self):
        text = 'Empresa de transporte de carga, logistica y almacen'
        best_name, best_score = self.classifier.get_best_industry(text)
        self.assertEqual(best_name, 'Transporte de carga general')
        self.assertGreater(best_score, 0)


class TestRelevanceScorer(TestCase):
    def setUp(self):
        self.scorer = RelevanceScorer()

    def test_high_score_transporte(self):
        result = self.scorer.score(
            'Transportes del Norte',
            'Empresa de transporte de carga pesada y logistica con flotilla de camiones'
        )
        self.assertGreaterEqual(result['score'], 30)
        self.assertIn(result['priority'], ['alta', 'media'])

    def test_excluded(self):
        result = self.scorer.score(
            'Cafeteria El Buen Sabor',
            'Restaurante y cafeteria'
        )
        self.assertEqual(result['score'], 0)
        self.assertTrue(result['is_excluded'])

    def test_low_score(self):
        result = self.scorer.score(
            'Oficina Administrativa',
            'Servicios administrativos y ofimatica'
        )
        self.assertLess(result['score'], 30)

    def test_product_bonus(self):
        result = self.scorer.score(
            'Remolques del Valle',
            'Venta de remolques tipo plataforma y cajas secas para transporte'
        )
        self.assertGreater(result['score'], 20)


class TestLeadFilter(TestCase):
    def setUp(self):
        self.filter = LeadFilter(threshold=30)

    def test_filter_by_threshold(self):
        records = [
            {'score_info': {'score': 80, 'priority': 'alta'}},
            {'score_info': {'score': 20, 'priority': 'baja'}},
            {'score_info': {'score': 50, 'priority': 'media'}},
        ]
        relevant, discarded = self.filter.filter_records(records)
        self.assertEqual(len(relevant), 2)
        self.assertEqual(len(discarded), 1)

    def test_prioritize_order(self):
        records = [
            {'score_info': {'score': 50, 'priority': 'media'}},
            {'score_info': {'score': 80, 'priority': 'alta'}},
        ]
        sorted_records = self.filter.prioritize(records)
        self.assertEqual(
            sorted_records[0]['score_info']['priority'], 'alta'
        )

    def test_summary_stats(self):
        records = [
            {'score_info': {'score': 80, 'priority': 'alta'}},
            {'score_info': {'score': 20, 'priority': 'baja'}},
        ]
        stats = self.filter.summary_stats(records)
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['relevant'], 1)


class TestPipeline(TestCase):
    def test_full_pipeline_with_csv(self):
        csv_content = (
            b'nombre,giro,ciudad\n'
            b'Transportes del Norte,Transporte de carga pesada,Monterrey\n'
            b'Cafeteria Central,Restaurante y cafeteria,CDMX\n'
            b'Constructora MX,Construccion de edificios,Guadalajara\n'
        )
        pipeline = PreprocessingPipeline(threshold=30)
        result = pipeline.process('test.csv', csv_content)

        self.assertIsNone(result.error)
        self.assertEqual(result.total_records, 3)
        self.assertGreaterEqual(result.relevant_records, 2)
        self.assertIsNotNone(result.cleaned_file_path)
        self.assertGreater(result.processing_time, 0)

        if result.cleaned_file_path and os.path.exists(result.cleaned_file_path):
            os.unlink(result.cleaned_file_path)

    def test_pipeline_stats_structure(self):
        csv_content = b'nombre,giro\nTest A,Transporte\nTest B,Cafeteria\n'
        pipeline = PreprocessingPipeline(threshold=30)
        result = pipeline.process('test.csv', csv_content)

        self.assertIn('total', result.stats)
        self.assertIn('relevant', result.stats)
        self.assertIn('discarded', result.stats)
        self.assertIn('avg_score', result.stats)

    def test_pipeline_empty_file(self):
        pipeline = PreprocessingPipeline()
        result = pipeline.process('empty.csv', b'')
        self.assertIsNotNone(result.error)


class TestExportService(TestCase):
    def setUp(self):
        self.exporter = ExportService()

    def test_export_csv(self):
        records = [
            {'name': 'Empresa A', 'score': '80'},
            {'name': 'Empresa B', 'score': '50'},
        ]
        path = self.exporter.export_csv(records)
        self.assertTrue(os.path.exists(path))
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('Empresa A', content)
        os.unlink(path)

    def test_export_empty(self):
        path = self.exporter.export_csv([])
        self.assertTrue(os.path.exists(path))
        os.unlink(path)


class TestFase3Scenarios(TestCase):
    """Escenarios CRISP-ML(Q) Fase 3: SQL/Borderline/Exclusion."""

    # ── 2a) Caso Ideal: SQL / Alta Prioridad ──────────────────────────
    def test_sql_alta_prioridad_arrendamiento_flotas(self):
        """
        Empresa de transporte pesado que menciona 'arrendamiento financiero
        de flotas' debe obtener score > 60, prioridad 'alta' y
        lead_intent_type = 'SQL'.
        """
        scorer = RelevanceScorer()
        result = scorer.score(
            'Transportes Pesados del Valle SA',
            'Empresa de transporte de carga pesada dedicada al '
            'arrendamiento financiero de flotas de tractocamiones '
            'y semirremolques para logistica industrial',
        )
        self.assertGreater(
            result['score'], 60,
            'El score debe superar 60 para ser prioridad alta',
        )
        self.assertEqual(
            result['priority'], 'alta',
            'Prioridad debe ser alta para score > 60',
        )
        self.assertEqual(
            result['lead_intent_type'], 'SQL',
            'lead_intent_type debe ser SQL al detectar intencion financiera',
        )
        self.assertFalse(
            result['is_excluded'],
            'No debe estar excluido',
        )

    # ── 2b) Caso Borderline: Rescate Lexico Difuso ────────────────────
    def test_borderline_fuzzy_classifier_rescue_typos(self):
        """
        El clasificador difuso (Fase 2) debe rescatar texto con typos
        mayores como 'trasportes' y 'rremoleques'.
        """
        classifier = IndustryClassifier()
        text = 'empresa de trasportes y rremoleques para carga pesada'
        results = classifier.classify(text)
        self.assertIn(
            'transporte_carga', results,
            'El clasificador difuso debe detectar transporte_carga '
            'pese a los typos',
        )
        self.assertGreater(
            results['transporte_carga']['score'], 0,
            'El score de la industria debe ser > 0',
        )

    def test_borderline_fuzzy_pipeline_rescue_typos(self):
        """
        El pipeline completo debe rescatar un registro con typos
        superando el threshold de 30.
        """
        csv_content = (
            b'nombre,giro\n'
            b'Empresa de Trasportes y Rremoleques,'
            b'Servicios de trasporte y rremoleques para carga pesada\n'
        )
        pipeline = PreprocessingPipeline(threshold=30)
        result = pipeline.process('test_typos.csv', csv_content)

        self.assertIsNone(
            result.error,
            'Pipeline no debe reportar error',
        )
        self.assertEqual(
            result.total_records, 1,
            'Debe haber 1 registro procesado',
        )
        self.assertGreaterEqual(
            result.relevant_records, 1,
            'El registro con typos debe ser relevante (score >= 30)',
        )

        record = result.records[0]
        score = record['_preprocess_score']
        self.assertGreaterEqual(
            score, 30,
            f'El score del registro rescatado ({score}) debe ser >= 30',
        )

        if result.cleaned_file_path and os.path.exists(result.cleaned_file_path):
            os.unlink(result.cleaned_file_path)

    # ── 2c) Caso de Exclusion Directa ─────────────────────────────────
    def test_exclusion_directa_cafeteria(self):
        """
        Registro con 'cafeteria gourmet' debe ser excluido de forma
        fulminante: score=0, is_excluded=True.
        """
        scorer = RelevanceScorer()
        result = scorer.score(
            'Cafeteria Gourmet SA',
            'Cafeteria gourmet y reposteria fina',
        )
        self.assertEqual(
            result['score'], 0,
            'El score debe ser 0 por exclusion',
        )
        self.assertTrue(
            result['is_excluded'],
            'is_excluded debe ser True',
        )
        self.assertEqual(
            result['priority'], 'descartado',
            'La prioridad debe ser descartado',
        )

    def test_exclusion_directa_jardin_ninos(self):
        """
        Registro con 'jardin de ninos' debe ser excluido de forma
        fulminante: score=0, is_excluded=True.
        """
        scorer = RelevanceScorer()
        result = scorer.score(
            'Jardin de Ninos Arcoiris',
            'Guarderia y jardin de ninos educacion inicial',
        )
        self.assertEqual(
            result['score'], 0,
            'El score debe ser 0 por exclusion',
        )
        self.assertTrue(
            result['is_excluded'],
            'is_excluded debe ser True',
        )
        self.assertEqual(
            result['priority'], 'descartado',
            'La prioridad debe ser descartado',
        )
