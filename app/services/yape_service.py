import csv
import io
import logging
import uuid
from datetime import datetime

import openpyxl
from sqlalchemy.exc import IntegrityError

from app.models import Expense, YapeTransaction, db

logger = logging.getLogger(__name__)


import json

from app.services.llm_automation_service import analyze_transaction_message


class YapeService:
    """Procesa transacciones Yape/Plin desde CSV/Excel"""

    EXPENSE_KEYWORDS = ['compra', 'pago', 'factura', 'proveedor', 'servicio', 'transporte']
    EXPENSE_INDICATORS = ['salida', 'egreso', 'cargo', '-']

    def __init__(self):
        self.batch_id = str(uuid.uuid4())
        self.stats = {'total_rows': 0, 'processed': 0, 'duplicates_skipped': 0, 'errors': 0, 'expenses_created': 0}

    def parse_yape_csv(self, file_stream, encoding='utf-8'):
        """Parsea CSV de Yape, retorna generator pa' no saturar RAM"""
        try:
            if isinstance(file_stream, bytes):
                file_stream = io.StringIO(file_stream.decode(encoding))
            elif isinstance(file_stream, str):
                file_stream = io.StringIO(file_stream)

            reader = csv.DictReader(file_stream)

            if not reader.fieldnames:
                raise ValueError('CSV vacío o sin encabezados')

            for row_num, row in enumerate(reader, start=2):
                try:
                    transaction = self._map_csv_row(row)
                    if transaction:
                        yield transaction
                except Exception as e:
                    logger.warning(f'Error procesando fila {row_num}: {str(e)}')
                    self.stats['errors'] += 1

        except Exception as e:
            logger.error(f'Error al parsear CSV: {str(e)}')
            raise ValueError(f'No se pudo leer CSV: {str(e)}')

    def parse_yape_excel(self, file_stream):
        """Parsea Excel Yape (XLSX) desde Flask"""
        try:
            workbook = openpyxl.load_workbook(file_stream, data_only=True)
            worksheet = workbook.active

            raw_data = []
            max_col = 1
            for row in worksheet.rows:
                row_vals = [cell.value for cell in row]
                raw_data.append(row_vals)
                max_col = max(max_col, len(row_vals))

            if not raw_data:
                raise ValueError('Excel sin datos legibles')

            header_row_idx = -1
            headers = []
            keywords = ['monto', 'fecha', 'operación', 'destino', 'origen', 'mensaje', 'tipo de transacción']

            for i, row in enumerate(raw_data):
                if not any(v is not None for v in row):
                    continue

                potential_headers = [str(v).strip().lower() if v is not None else '' for v in row]
                matches = sum(1 for h in potential_headers if any(kw in h for kw in keywords))

                if matches >= 2:
                    headers = [str(v).strip() if v is not None else None for v in row]
                    header_row_idx = i
                    logger.info(f'Encabezado detectado en fila {i + 1}: {headers}')
                    break

            if header_row_idx == -1:
                for i, row in enumerate(raw_data):
                    non_empty = [v for v in row if v is not None and str(v).strip()]
                    if len(non_empty) >= 4:
                        headers = [str(v).strip() if v is not None else None for v in row]
                        header_row_idx = i
                        logger.warning(f'Usando fila {i + 1} como header por densidad')
                        break

            if header_row_idx == -1:
                raise ValueError('No se encontró una tabla de datos válida en el Excel')

            for r_idx in range(header_row_idx + 1, len(raw_data)):
                row = raw_data[r_idx]
                if not any(v is not None for v in row):
                    continue

                row_dict = {}
                for c_idx in range(min(len(headers), len(row))):
                    col_name = headers[c_idx]
                    if col_name:
                        row_dict[col_name] = row[c_idx]

                try:
                    transaction = self._map_csv_row(row_dict)
                    if transaction:
                        yield transaction
                except Exception as e:
                    logger.warning(f'Error procesando fila {r_idx + 1}: {str(e)}')
                    self.stats['errors'] += 1

        except Exception as e:
            logger.error(f'Error crítico parseando Excel: {str(e)}')
            raise ValueError(f'Formato de Excel no compatible: {str(e)}')

    def _map_csv_row(self, row):
        """Mapea fila CSV a dict normalizado"""
        normalized_row = {k.strip().lower(): v for k, v in row.items() if k}

        operation_number = self._extract_field(
            normalized_row,
            [
                'número de operación',
                'operation #',
                'op_number',
                'transaction_id',
                'id',
                'referencia',
                'reference',
                'num_operacion',
                'nro de operacion',
                'nro operacion',
                'nro. operacion',
            ],
        )

        transaction_date = self._extract_field(
            normalized_row,
            [
                'fecha de operación',
                'fecha',
                'date',
                'transaction_date',
                'fecha transaccion',
                'fecha de operacion',
                'fecha de operaciã³n',
                'fecha operacion',
                'fecha de operación',
            ],
        )

        sender_name = self._extract_field(
            normalized_row,
            [
                'origen',
                'nombre',
                'razón social',
                'sender',
                'nombre del remitente',
                'from',
                'quien',
                'de',
                'remitente',
                'razon social',
                'nombre_emisor',
                'emisor',
                'contacto',
            ],
        )

        if not sender_name or str(sender_name).strip() == '':
            sender_name = self._extract_field(
                normalized_row, ['destino', 'to', 'para', 'beneficiario', 'nombre_receptor', 'receptor']
            )

        amount = self._extract_field(
            normalized_row, ['monto', 'amount', 'cantidad', 'importe', 'valor', 'monto total', 'valor transaccion']
        )
        message = self._extract_field(
            normalized_row,
            [
                'mensaje',
                'description',
                'nota',
                'message',
                'concepto',
                'tipo de transacción',
                'tipo de transaccion',
                'tipo',
                'comentario',
                'referencia',
            ],
        )

        if not operation_number or str(operation_number).strip().lower() in ['none', '', 'nan']:
            origin = self._extract_field(normalized_row, ['origen', 'from', 'sender', 'nombre'])
            destination = self._extract_field(normalized_row, ['destino', 'to', 'para', 'receptor'])

            date_str = str(transaction_date).replace(' ', '_').replace(':', '-')
            operation_number = f'HASH_{str(origin or "")[:5]}_{str(destination or "")[:5]}_{str(amount or 0).replace(".", "_")}_{date_str}'

        if not operation_number or amount is None:
            logger.debug('Fila incompleta: falta operation_number o amount')
            return None
            logger.debug('Fila incompleta: falta operation_number o amount')
            return None

        try:
            amount = float(str(amount).replace(',', '.').replace('S/', '').strip())
        except ValueError:
            logger.warning(f'Monto inválido: {amount}')
            return None

        try:
            if isinstance(transaction_date, str):
                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                    try:
                        transaction_date = datetime.strptime(transaction_date.strip(), fmt)
                        break
                    except ValueError:
                        continue
                else:
                    transaction_date = datetime.now()
            elif not isinstance(transaction_date, datetime):
                transaction_date = datetime.now()
        except Exception:
            logger.warning(f'Fecha inválida: {transaction_date}')
            transaction_date = datetime.now()

        operation_number = self._sanitize_string(operation_number)
        sender_name = self._sanitize_string(sender_name) or 'SIN_ESPECIFICAR'
        message = self._sanitize_string(message) or ''

        return {
            'operation_number': operation_number,
            'transaction_date': transaction_date,
            'sender_name': sender_name,
            'amount': amount,
            'message': message,
        }

    def _extract_field(self, row, possible_keys):
        """Busca valor en dict por múltiples keys"""
        for key in possible_keys:
            if key in row and row[key]:
                return row[key]
        return None

    def _sanitize_string(self, value):
        """Sanitiza string para prevenir XSS."""
        if not value:
            return None

        value = str(value).strip()

        dangerous_chars = ['<', '>', '"', "'", ';', '--', '/*', '*/']
        for char in dangerous_chars:
            value = value.replace(char, '')

        return value[:500] if value else None

    def import_transactions(self, file_stream, file_type='csv'):
        """Importa Yape con UPSERT pattern, retorna stats"""
        try:
            if file_type.lower() == 'xlsx' or file_type.lower() == 'xls':
                transactions = self.parse_yape_excel(file_stream)
            else:
                transactions = self.parse_yape_csv(file_stream)

            batch_id = self.batch_id
            logger.info(f'Iniciando importación Yape [Batch: {batch_id}]')

            try:
                for transaction_data in transactions:
                    self.stats['total_rows'] += 1

                    success = self._insert_or_ignore_transaction(transaction_data, batch_id)

                    if success:
                        self.stats['processed'] += 1

                        if self._is_important_expense(transaction_data):
                            self._create_expense_from_transaction(transaction_data)
                            self.stats['expenses_created'] += 1
                    else:
                        self.stats['duplicates_skipped'] += 1

                db.session.commit()
                logger.info(f'Importación completada: {self.stats}')

                return True, self.stats

            except Exception as e:
                db.session.rollback()
                logger.error(f'Error durante importación, ROLLBACK ejecutado: {str(e)}')
                self.stats['errors'] += 1
                return False, f'Error: {str(e)}'

        except Exception as e:
            logger.error(f'Error crítico en importación: {str(e)}')
            return False, f'Error crítico: {str(e)}'

    def _insert_or_ignore_transaction(self, transaction_data, batch_id):
        """Inserta si no existe, salta si ya está. True = insertado"""
        operation_number = transaction_data['operation_number']

        existing = YapeTransaction.query.filter_by(operation_number=operation_number).first()

        if existing:
            logger.debug(f'Transacción {operation_number} ya existe, skipping')
            return False

        yape_tx = YapeTransaction(
            operation_number=operation_number,
            transaction_date=transaction_data['transaction_date'],
            sender_name=transaction_data['sender_name'],
            amount=transaction_data['amount'],
            message=transaction_data['message'],
            category=self._categorize_transaction(transaction_data),
            import_batch_id=batch_id,
        )

        try:
            db.session.add(yape_tx)
            logger.debug(f'Transacción {operation_number} preparada para inserción')
            return True
        except IntegrityError as e:
            logger.debug(f'IntegrityError (duplicado?) {operation_number}: {str(e)}')
            db.session.rollback()
            return False

    def _categorize_transaction(self, transaction_data):
        """Clasifica la transacción usando IA si el mensaje es complejo."""
        message = (transaction_data.get('message') or '').lower()
        if not message:
            return 'unclassified'

        if any(kw in message for kw in ['pago', 'salario', 'terapista']):
            return 'therapist_payment'
        elif any(kw in message for kw in ['factura', 'proveedor', 'compra', 'servicio']):
            return 'operational'

        if len(message) > 10:
            try:
                ai_response = analyze_transaction_message(message)

                if '{' in ai_response:
                    ai_response = ai_response[ai_response.find('{') : ai_response.rfind('}') + 1]
                    data = json.loads(ai_response)
                    return data.get('category', 'unclassified')
            except Exception as e:
                logger.debug(f"IA omitida o con error para '{message}': {e}")

        if any(indicator in message for indicator in self.EXPENSE_INDICATORS):
            return 'expense'

        return 'unclassified'

    def _is_important_expense(self, transaction_data):
        """Determina si es un gasto importante que debe crearse automáticamente."""
        message = (transaction_data.get('message') or '').lower()
        amount = transaction_data.get('amount', 0)

        is_outflow = amount < 0 or 'salida' in message or 'gasto' in message

        has_keyword = any(kw in message for kw in self.EXPENSE_KEYWORDS)

        is_significant = abs(amount) > 50

        return (is_outflow or has_keyword) and is_significant

    def _create_expense_from_transaction(self, transaction_data):
        """Crea Expense desde YapeTransaction"""
        try:
            expense = Expense(
                category='operational',
                amount=abs(transaction_data['amount']),
                date=transaction_data['transaction_date'],
                description=f'Yape: {transaction_data["sender_name"]} - {transaction_data["message"]}',
                method='yape_plin',
                receipt_image_path=None,
            )
            db.session.add(expense)
            logger.info(f'Expense creado desde Yape: {transaction_data["operation_number"]}')
        except Exception as e:
            logger.warning(f'Error creando Expense: {str(e)}')

    def get_transactions_by_batch(self, batch_id):
        """Transacciones por lote"""
        return YapeTransaction.query.filter_by(import_batch_id=batch_id).all()

    def get_transactions_by_date_range(self, start_date, end_date):
        """Transacciones por rango de fechas"""
        return (
            YapeTransaction.query.filter(
                YapeTransaction.transaction_date >= start_date, YapeTransaction.transaction_date <= end_date
            )
            .order_by(YapeTransaction.transaction_date.desc())
            .all()
        )

    def get_unattached_expenses(self, limit=50):
        """Yape sin comprobante adjunto"""
        return (
            YapeTransaction.query.filter(YapeTransaction.receipt_image_path is None, YapeTransaction.is_expense)
            .order_by(YapeTransaction.transaction_date.desc())
            .limit(limit)
            .all()
        )

    def search_transactions(self, query, limit=20):
        """Búsqueda por operation_number, sender_name o message."""
        search_pattern = f'%{query}%'
        return (
            YapeTransaction.query.filter(
                (YapeTransaction.operation_number.ilike(search_pattern))
                | (YapeTransaction.sender_name.ilike(search_pattern))
                | (YapeTransaction.message.ilike(search_pattern))
            )
            .limit(limit)
            .all()
        )

    def attach_receipt_to_transaction(self, operation_number, receipt_path):
        """Adjunta foto/comprobante a YapeTransaction"""
        try:
            yape_tx = YapeTransaction.query.filter_by(operation_number=operation_number).first()

            if not yape_tx:
                return False, 'Transacción no encontrada'

            yape_tx.receipt_image_path = receipt_path
            yape_tx.updated_at = datetime.utcnow()
            db.session.commit()

            logger.info(f'Comprobante adjuntado a {operation_number}: {receipt_path}')
            return True, 'Comprobante guardado exitosamente'

        except Exception as e:
            db.session.rollback()
            logger.error(f'Error adjuntando comprobante: {str(e)}')
            return False, f'Error: {str(e)}'

    def get_import_stats(self):
        """Stats de la importación actual"""
        return self.stats

    def get_all_imports(self):
        """Obtiene historial de todos los lotes importados."""
        batch_ids = db.session.query(YapeTransaction.import_batch_id.distinct()).all()

        result = []
        for (batch_id,) in batch_ids:
            if not batch_id:
                continue

            batch_transactions = YapeTransaction.query.filter_by(import_batch_id=batch_id).all()

            result.append(
                {
                    'batch_id': batch_id,
                    'total': len(batch_transactions),
                    'amount_sum': sum(t.amount for t in batch_transactions),
                    'first_date': min(t.transaction_date for t in batch_transactions),
                    'last_date': max(t.transaction_date for t in batch_transactions),
                    'imported_at': batch_transactions[0].created_at if batch_transactions else None,
                }
            )

        return sorted(result, key=lambda x: x['imported_at'], reverse=True)
