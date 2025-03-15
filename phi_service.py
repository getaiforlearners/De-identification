from typing import List, Dict, Any
import logging
from phi_detector import PHIDetector
from db_connector import DatabaseConnector

logger = logging.getLogger(__name__)

class PHIService:
    """Service class to handle PHI detection and database operations"""

    def __init__(self):
        self.detector = PHIDetector()

    def analyze_database_columns(self, connection: DatabaseConnector, table_name: str, selected_columns: List[str] = None, detection_mode: str = 'pattern') -> Dict[str, Any]:
        """
        Analyze columns in a database table for PHI content.

        Args:
            connection: Database connection
            table_name: Name of the table to analyze
            selected_columns: List of column names to analyze (if None, analyze all text columns)
            detection_mode: 'pattern' for regex-based or 'ai' for AI-powered detection
        """
        try:
            # Get column information
            columns = connection.get_columns(table_name)

            results = {
                'table_name': table_name,
                'columns': []
            }

            # Filter columns if specific ones are selected
            if selected_columns:
                columns = [col for col in columns if col['name'] in selected_columns]

            # Analyze text-based columns
            text_types = ['varchar', 'text', 'char', 'string']
            for column in columns:
                col_type = column['type'].lower()
                if any(text_type in col_type for text_type in text_types):
                    # Sample data from the column
                    query = f"SELECT DISTINCT {column['name']} FROM {table_name} LIMIT 1000"
                    df = connection.execute_query(query)

                    if not df.empty:
                        sample_data = df[column['name']].dropna().astype(str).tolist()

                        # Get detector configuration based on mode
                        detector_config = {'ai_enabled': detection_mode == 'ai'}

                        # Analyze the column with column name context
                        analysis = self.detector.analyze_database_column(
                            column_name=column['name'], 
                            sample_data=sample_data
                        )

                        # Only include if PHI is detected
                        if analysis['phi_types']:
                            results['columns'].append({
                                'name': column['name'],
                                'type': column['type'],
                                'analysis': analysis
                            })

            return results

        except Exception as e:
            logger.error(f"Error analyzing table {table_name}: {str(e)}")
            return {'error': str(e)}

    def suggest_deidentification_plan(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a de-identification plan based on analysis results.
        """
        plan = {
            'table_name': analysis_results['table_name'],
            'columns': []
        }

        for column in analysis_results['columns']:
            column_plan = {
                'name': column['name'],
                'detected_phi': [],
                'suggested_actions': []
            }

            # Process each type of PHI found
            for phi_type in column['analysis']['phi_types']:
                if phi_type['frequency'] > 0.1:  # Only suggest actions if PHI appears in >10% of rows
                    column_plan['detected_phi'].append({
                        'type': phi_type['type'],
                        'frequency': phi_type['frequency'],
                        'confidence': phi_type['avg_confidence']
                    })

                    # Get suggestions for this type of PHI with column context
                    suggestions = self.detector.suggest_deidentification([{
                        'type': phi_type['type'],
                        'value': phi_type['example_values'][0] if phi_type['example_values'] else '',
                        'confidence': phi_type['avg_confidence']
                    }], column_name=column['name'])

                    for suggestion in suggestions:
                        column_plan['suggested_actions'].extend(suggestion['methods'])

            if column_plan['detected_phi']:
                plan['columns'].append(column_plan)

        return plan

    def execute_deidentification(self, connection: DatabaseConnector, plan: Dict[str, Any], target_schema: str) -> Dict[str, Any]:
        """
        Execute a de-identification plan on the database.
        Creates de-identified copies in the target schema.
        """
        try:
            results = {
                'table_name': plan['table_name'],
                'status': 'success',
                'columns_processed': [],
                'rows_affected': 0
            }

            # Create target schema if it doesn't exist
            connection.execute_query(f"CREATE SCHEMA IF NOT EXISTS {target_schema}")

            # Get all columns from source table
            all_columns = connection.get_columns(plan['table_name'])
            column_list = [col['name'] for col in all_columns]

            # Build the SELECT statement for the new table
            select_parts = []
            for col_name in column_list:
                # Check if this column needs de-identification
                col_plan = next((c for c in plan['columns'] if c['name'] == col_name), None)

                if col_plan and col_plan['suggested_actions']:
                    # Apply de-identification transformations based on the highest priority action
                    action = min(col_plan['suggested_actions'], key=lambda x: x.get('priority', 999))
                    transform = self._build_transformation_sql(col_name, action['method'])
                    select_parts.append(f"{transform} as {col_name}")
                    results['columns_processed'].append({
                        'name': col_name,
                        'method': action['method']
                    })
                else:
                    # Keep column as-is
                    select_parts.append(col_name)

            # Create the de-identified table
            create_query = f"""
            CREATE TABLE {target_schema}.{plan['table_name']}_deidentified AS 
            SELECT {', '.join(select_parts)}
            FROM {plan['table_name']}
            """

            connection.execute_query(create_query)

            # Get row count
            count_query = f"SELECT COUNT(*) as cnt FROM {target_schema}.{plan['table_name']}_deidentified"
            count_df = connection.execute_query(count_query)
            results['rows_affected'] = count_df['cnt'].iloc[0] if not count_df.empty else 0

            return results

        except Exception as e:
            logger.error(f"Error executing de-identification plan: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _build_transformation_sql(self, column_name: str, method: str) -> str:
        """
        Build SQL transformation for de-identification.
        """
        if method == 'hash':
            return f"MD5({column_name}::text)"
        elif method == 'mask':
            return f"REGEXP_REPLACE({column_name}::text, '.*', '***')"
        elif method == 'truncate':
            return f"LEFT({column_name}::text, 3)"
        elif method == 'redact':
            return "'[REDACTED]'"
        elif method == 'shift':
            return f"({column_name}::timestamp + INTERVAL '1 day' * FLOOR(RANDOM() * 365))"
        elif method == 'generalize':
            return f"DATE_TRUNC('month', {column_name}::timestamp)"
        elif method == 'smart_redact':
            # Advanced redaction that preserves context
            return f"REGEXP_REPLACE({column_name}::text, '\\b(\\w+@\\w+\\.\\w+|\\d{{3}}-\\d{{2}}-\\d{{4}})\\b', '[REDACTED]')"
        elif method == 'consistent_hash':
            # Use a deterministic hash for consistent replacement
            return f"ENCODE(DIGEST({column_name}::text, 'sha256'), 'hex')"
        elif method == 'pseudonym':
            # Simple pseudonymization using a hash prefix
            return f"'PSEUDO_' || SUBSTR(MD5({column_name}::text), 1, 8)"
        elif method == 'k_anonymize':
            # Basic k-anonymization by grouping
            return f"CASE WHEN COUNT(*) OVER (PARTITION BY {column_name}) < 5 THEN '[ANONYMIZED]' ELSE {column_name}::text END"
        else:
            return column_name