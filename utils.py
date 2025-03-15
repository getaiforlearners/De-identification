import os
import pandas as pd
import tempfile
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def generate_report(process_log, stats):
    """Generate a report file for a de-identification process."""
    # Create report directory if it doesn't exist
    report_dir = os.path.join(os.getcwd(), 'reports')
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
    
    # Generate report filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"deident_report_{process_log.id}_{timestamp}.csv"
    report_path = os.path.join(report_dir, filename)
    
    # Create report data
    report_data = []
    
    # Add summary information
    report_data.append({
        'Category': 'Summary',
        'Item': 'Process Name',
        'Value': process_log.process_name
    })
    report_data.append({
        'Category': 'Summary',
        'Item': 'Start Time',
        'Value': process_log.start_time.strftime('%Y-%m-%d %H:%M:%S')
    })
    report_data.append({
        'Category': 'Summary',
        'Item': 'End Time',
        'Value': process_log.end_time.strftime('%Y-%m-%d %H:%M:%S') if process_log.end_time else 'N/A'
    })
    report_data.append({
        'Category': 'Summary',
        'Item': 'Status',
        'Value': process_log.status
    })
    report_data.append({
        'Category': 'Summary',
        'Item': 'Total Records Processed',
        'Value': stats.get('total_records', 0)
    })
    report_data.append({
        'Category': 'Summary',
        'Item': 'Records Modified',
        'Value': stats.get('modified_records', 0)
    })
    report_data.append({
        'Category': 'Summary',
        'Item': 'Tables Processed',
        'Value': stats.get('tables_processed', 0)
    })
    
    # Add field modification details
    fields_modified = stats.get('fields_modified', {})
    for field, count in fields_modified.items():
        report_data.append({
            'Category': 'Field Modifications',
            'Item': field,
            'Value': count
        })
    
    # Create DataFrame and save to CSV
    report_df = pd.DataFrame(report_data)
    report_df.to_csv(report_path, index=False)
    
    logger.info(f"Generated report: {report_path}")
    return report_path

def save_to_temp(data, prefix='temp_', suffix='.json'):
    """Save data to a temporary file and return the path."""
    # Create temp directory if it doesn't exist
    temp_dir = os.path.join(os.getcwd(), 'temp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    # Create temp file
    fd, temp_path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=temp_dir)
    
    try:
        with os.fdopen(fd, 'w') as f:
            if isinstance(data, dict) or isinstance(data, list):
                json.dump(data, f)
            else:
                f.write(str(data))
        return temp_path
    except Exception as e:
        logger.error(f"Error saving to temp file: {str(e)}")
        return None

def validate_rule_config(rule_type, config):
    """Validate a rule configuration."""
    required_fields = {
        'patient_id': ['prefix', 'format', 'tables', 'columns'],
        'date_offset': ['min_days', 'max_days', 'tables', 'columns'],
        'date_generalization': ['level', 'tables', 'columns'],
        'phone_mask': ['pattern', 'tables', 'columns'],
        'email_mask': ['mode', 'tables', 'columns'],
        'text_redaction': ['patterns', 'replacement', 'tables', 'columns'],
        'fixed_value': ['value', 'tables', 'columns'],
        'hash': ['salt', 'length', 'tables', 'columns'],
        'random_value': ['tables', 'columns'],
        'zipcode_truncate': ['tables', 'columns']
    }
    
    # Check if rule type is supported
    if rule_type not in required_fields:
        return False, f"Unsupported rule type: {rule_type}"
    
    # Check for required fields
    for field in required_fields[rule_type]:
        if field not in config:
            return False, f"Missing required field '{field}' for rule type '{rule_type}'"
    
    return True, "Valid configuration"

def get_db_driver_name(db_type):
    """Get the appropriate database driver name."""
    if db_type.lower() == 'mysql':
        return 'mysql-connector-python'
    elif db_type.lower() == 'postgresql':
        return 'psycopg2'
    elif db_type.lower() == 'sqlserver':
        return 'pyodbc'
    else:
        return None
