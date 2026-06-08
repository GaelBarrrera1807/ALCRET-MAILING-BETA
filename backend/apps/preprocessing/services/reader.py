import csv
import io
import logging
import tempfile

import pandas as pd

logger = logging.getLogger(__name__)


class FileReader:
    SUPPORTED_EXTENSIONS = ('.csv', '.xlsx', '.xls')

    def read(self, filename, file_bytes):
        ext = self._get_extension(filename)
        if ext == '.csv':
            return self._read_csv(file_bytes)
        return self._read_excel(file_bytes)

    def _get_extension(self, filename):
        name = filename.lower()
        for ext in self.SUPPORTED_EXTENSIONS:
            if name.endswith(ext):
                return ext
        raise ValueError(
            f'Formato no soportado: {filename}. '
            f'Use: {", ".join(self.SUPPORTED_EXTENSIONS)}'
        )

    def _read_csv(self, file_bytes):
        try:
            content = file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            content = file_bytes.decode('latin-1')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            return []
        fieldnames = reader.fieldnames or list(rows[0].keys())
        logger.info(f'CSV parsed: {len(rows)} rows, columns: {fieldnames}')
        return rows

    def _read_excel(self, file_bytes):
        with tempfile.NamedTemporaryFile(suffix='.xlsx') as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            df = pd.read_excel(tmp.name, engine='openpyxl')
        df = df.where(pd.notna(df), None)
        rows = df.to_dict('records')
        logger.info(f'Excel parsed: {len(rows)} rows, columns: {list(df.columns)}')
        return rows
