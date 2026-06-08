import csv
import io
import logging
import os
import tempfile

import pandas as pd

logger = logging.getLogger(__name__)


class ExportService:
    @staticmethod
    def _sanitize_csv_value(value: str) -> str:
        if value and value[0] in ('=', '+', '-', '@', '\t', '\r'):
            return "'" + value
        return value

    def export_csv(self, records, output_path=None):
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix='.csv')
            os.close(fd)
        if not records:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                f.write('')
            return output_path
        fieldnames = list(records[0].keys())
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in records:
                cleaned = {
                    k: self._sanitize_csv_value(str(v) if v is not None else '')
                    for k, v in row.items()
                }
                writer.writerow(cleaned)
        return output_path

    def export_excel(self, records, output_path=None):
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix='.xlsx')
            os.close(fd)
        df = pd.DataFrame(records)
        df = df.where(pd.notna(df), None)
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Relevantes')
        return output_path

    def generate_cleaned_file(self, records, original_filename, fmt=None):
        if fmt is None:
            ext = os.path.splitext(original_filename)[1].lower()
            fmt = 'xlsx' if ext in ('.xlsx', '.xls') else 'csv'
        if fmt == 'csv':
            return self.export_csv(records)
        return self.export_excel(records)

    def export_with_metadata(self, records, original_filename, output_dir=None):
        if not records:
            logger.warning('No records to export')
            return None
        ext = os.path.splitext(original_filename)[1].lower()
        clean_name = f'preprocessed_{os.path.splitext(original_filename)[0]}{ext}'
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, clean_name)
        else:
            fd, output_path = tempfile.mkstemp(suffix=ext)
            os.close(fd)
        if ext in ('.xlsx', '.xls'):
            return self.export_excel(records, output_path)
        return self.export_csv(records, output_path)
