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
        text = 'Tienda de abarrotes y miscelanea'
        results = self.classifier.classify(text)
        for key, info in results.items():
            self.assertEqual(info['score'], 0)

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
