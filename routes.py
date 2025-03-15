from flask import render_template, request, jsonify, redirect, url_for, flash, session
import pandas as pd
import json
import logging
import os
import time
import random
import datetime
from sqlalchemy import text, exc, func

from app import app, db
from models import (
    DBConnection, DeidentRule, MappingTable, ProcessLog, 
    PatientMaster, EncounterMaster, PHIAttributeMaster, SavedQuery
)
from db_connector import DatabaseConnector
from deidentifier import Deidentifier
from rule_engine import RuleEngine
from utils import generate_report, save_to_temp
from phi_service import PHIService

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Home page - shows dashboard with stats and links."""
    # Get database connection count
    conn_count = DBConnection.query.count()
    
    # Get rule count
    rule_count = DeidentRule.query.count()
    
    # Get mapping table count
    mapping_count = MappingTable.query.count()
    
    # Get recent process logs
    recent_logs = ProcessLog.query.order_by(ProcessLog.start_time.desc()).limit(5).all()
    
    return render_template('index.html', 
                           conn_count=conn_count,
                           rule_count=rule_count,
                           mapping_count=mapping_count,
                           recent_logs=recent_logs)

@app.route('/connections')
def connections():
    """Database connections management page."""
    # Get all database connections
    connections = DBConnection.query.all()
    return render_template('connections.html', connections=connections)

@app.route('/connections/add', methods=['GET', 'POST'])
def add_connection():
    """Add a new database connection."""
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        db_type = request.form.get('db_type')
        host = request.form.get('host')
        port = request.form.get('port')
        database = request.form.get('database')
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Validate input
        if not name or not db_type or not host or not port or not database or not username or not password:
            flash('All fields are required', 'danger')
            return redirect(url_for('add_connection'))
        
        # Create new connection
        new_connection = DBConnection(
            name=name,
            db_type=db_type,
            host=host,
            port=int(port),
            database=database,
            username=username,
            password=password
        )
        
        # Test the connection before saving
        try:
            connector = DatabaseConnector(
                db_type=db_type,
                host=host,
                port=int(port),
                database=database,
                username=username,
                password=password
            )
            if connector.connect():
                # Save to database if connection successful
                db.session.add(new_connection)
                db.session.commit()
                flash('Connection added successfully', 'success')
                return redirect(url_for('connections'))
            else:
                flash('Could not connect to database with these settings', 'danger')
        except Exception as e:
            flash(f'Error testing connection: {str(e)}', 'danger')
        
        return redirect(url_for('add_connection'))
    
    # GET request - show the form
    return render_template('connections.html', add_mode=True)

@app.route('/connections/edit/<int:conn_id>', methods=['GET', 'POST'])
def edit_connection(conn_id):
    """Edit an existing database connection."""
    # Find the connection
    connection = DBConnection.query.get_or_404(conn_id)
    
    if request.method == 'POST':
        # Get form data
        connection.name = request.form.get('name')
        connection.db_type = request.form.get('db_type')
        connection.host = request.form.get('host')
        connection.port = int(request.form.get('port'))
        connection.database = request.form.get('database')
        connection.username = request.form.get('username')
        
        # Only update password if provided
        if request.form.get('password'):
            connection.password = request.form.get('password')
        
        # Test the connection before saving
        try:
            connector = DatabaseConnector(
                db_type=connection.db_type,
                host=connection.host,
                port=connection.port,
                database=connection.database,
                username=connection.username,
                password=connection.password
            )
            if connector.connect():
                # Save to database if connection successful
                db.session.commit()
                flash('Connection updated successfully', 'success')
                return redirect(url_for('connections'))
            else:
                flash('Could not connect to database with these settings', 'danger')
        except Exception as e:
            flash(f'Error testing connection: {str(e)}', 'danger')
        
        return redirect(url_for('edit_connection', conn_id=conn_id))
    
    # GET request - show the form
    return render_template('connections.html', connection=connection, edit_mode=True)

@app.route('/connections/delete/<int:conn_id>', methods=['POST'])
def delete_connection(conn_id):
    """Delete a database connection."""
    connection = DBConnection.query.get_or_404(conn_id)
    db.session.delete(connection)
    db.session.commit()
    flash('Connection deleted successfully', 'success')
    return redirect(url_for('connections'))

@app.route('/connections/test/<int:conn_id>')
def test_connection(conn_id):
    """Test a database connection."""
    connection = DBConnection.query.get_or_404(conn_id)
    
    try:
        connector = DatabaseConnector(
            db_type=connection.db_type,
            host=connection.host,
            port=connection.port,
            database=connection.database,
            username=connection.username,
            password=connection.password
        )
        if connector.connect():
            # Get list of tables if connection successful
            tables = connector.get_tables()
            connector.disconnect()
            return jsonify({
                'success': True,
                'message': f'Successfully connected to {connection.name}',
                'tables': tables
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Could not connect to database'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/rules')
def rules():
    """De-identification rules management page."""
    # Get all rules
    rules = DeidentRule.query.all()
    return render_template('rules.html', rules=rules)

@app.route('/rules/add', methods=['GET', 'POST'])
def add_rule():
    """Add a new de-identification rule."""
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        description = request.form.get('description')
        rule_type = request.form.get('rule_type')
        
        # Get the configuration based on rule type
        config = {}
        
        if rule_type == 'patient_id':
            config = {
                'prefix': request.form.get('prefix', 'P'),
                'format': request.form.get('format', '{}{:07d}'),
                'tables': request.form.get('tables', '.*').split(','),
                'columns': request.form.get('columns', '.*id.*').split(',')
            }
        elif rule_type == 'date_offset':
            config = {
                'min_days': int(request.form.get('min_days', -30)),
                'max_days': int(request.form.get('max_days', 30)),
                'seed': int(request.form.get('seed', 42)),
                'tables': request.form.get('tables', '.*').split(','),
                'columns': request.form.get('columns', '.*date.*').split(',')
            }
        elif rule_type == 'phone_mask':
            config = {
                'pattern': request.form.get('pattern', 'XXX-XXX-{last4}'),
                'tables': request.form.get('tables', '.*').split(','),
                'columns': request.form.get('columns', '.*phone.*').split(',')
            }
        elif rule_type == 'email_mask':
            config = {
                'mode': request.form.get('mode', 'preserve_domain'),
                'tables': request.form.get('tables', '.*').split(','),
                'columns': request.form.get('columns', '.*email.*').split(',')
            }
        elif rule_type == 'text_redaction':
            patterns = request.form.get('patterns', r'\b\d{3}-\d{2}-\d{4}\b')
            config = {
                'patterns': patterns.split(','),
                'replacement': request.form.get('replacement', '[REDACTED]'),
                'tables': request.form.get('tables', '.*').split(','),
                'columns': request.form.get('columns', '.*notes.*').split(',')
            }
        else:
            # Generic configuration for other rule types
            for key, value in request.form.items():
                if key not in ['name', 'description', 'rule_type']:
                    config[key] = value
            
            # Always include tables and columns patterns
            if 'tables' not in config:
                config['tables'] = request.form.get('tables', '.*').split(',')
            if 'columns' not in config:
                config['columns'] = request.form.get('columns', '.*').split(',')
        
        # Create new rule
        new_rule = DeidentRule(
            name=name,
            description=description,
            rule_type=rule_type,
            config=json.dumps(config)
        )
        
        db.session.add(new_rule)
        db.session.commit()
        flash('Rule added successfully', 'success')
        return redirect(url_for('rules'))
    
    # GET request - show the form
    return render_template('rules.html', add_mode=True)

@app.route('/rules/edit/<int:rule_id>', methods=['GET', 'POST'])
def edit_rule(rule_id):
    """Edit an existing de-identification rule."""
    rule = DeidentRule.query.get_or_404(rule_id)
    
    if request.method == 'POST':
        # Update rule basic info
        rule.name = request.form.get('name')
        rule.description = request.form.get('description')
        
        # Get the configuration based on rule type
        config = {}
        
        if rule.rule_type == 'patient_id':
            config = {
                'prefix': request.form.get('prefix', 'P'),
                'format': request.form.get('format', '{}{:07d}'),
                'tables': request.form.get('tables', '.*').split(','),
                'columns': request.form.get('columns', '.*id.*').split(',')
            }
        elif rule.rule_type == 'date_offset':
            config = {
                'min_days': int(request.form.get('min_days', -30)),
                'max_days': int(request.form.get('max_days', 30)),
                'seed': int(request.form.get('seed', 42)),
                'tables': request.form.get('tables', '.*').split(','),
                'columns': request.form.get('columns', '.*date.*').split(',')
            }
        elif rule.rule_type == 'phone_mask':
            config = {
                'pattern': request.form.get('pattern', 'XXX-XXX-{last4}'),
                'tables': request.form.get('tables', '.*').split(','),
                'columns': request.form.get('columns', '.*phone.*').split(',')
            }
        elif rule.rule_type == 'email_mask':
            config = {
                'mode': request.form.get('mode', 'preserve_domain'),
                'tables': request.form.get('tables', '.*').split(','),
                'columns': request.form.get('columns', '.*email.*').split(',')
            }
        elif rule.rule_type == 'text_redaction':
            patterns = request.form.get('patterns', r'\b\d{3}-\d{2}-\d{4}\b')
            config = {
                'patterns': patterns.split(','),
                'replacement': request.form.get('replacement', '[REDACTED]'),
                'tables': request.form.get('tables', '.*').split(','),
                'columns': request.form.get('columns', '.*notes.*').split(',')
            }
        else:
            # Generic configuration for other rule types
            for key, value in request.form.items():
                if key not in ['name', 'description', 'rule_type']:
                    config[key] = value
            
            # Always include tables and columns patterns
            if 'tables' not in config:
                config['tables'] = request.form.get('tables', '.*').split(',')
            if 'columns' not in config:
                config['columns'] = request.form.get('columns', '.*').split(',')
        
        rule.config = json.dumps(config)
        db.session.commit()
        flash('Rule updated successfully', 'success')
        return redirect(url_for('rules'))
    
    # GET request - show the form with current values
    return render_template('rules.html', rule=rule, edit_mode=True)

@app.route('/rules/delete/<int:rule_id>', methods=['POST'])
def delete_rule(rule_id):
    """Delete a de-identification rule."""
    rule = DeidentRule.query.get_or_404(rule_id)
    db.session.delete(rule)
    db.session.commit()
    flash('Rule deleted successfully', 'success')
    return redirect(url_for('rules'))

@app.route('/mappings')
def mappings():
    """Mapping tables management page."""
    # Get all mapping tables with their connections
    mappings = MappingTable.query.all()
    connections = DBConnection.query.all()
    return render_template('mappings.html', mappings=mappings, connections=connections)

@app.route('/mappings/add', methods=['GET', 'POST'])
def add_mapping():
    """Add a new mapping table configuration."""
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        source_table = request.form.get('source_table')
        destination_table = request.form.get('destination_table')
        join_key = request.form.get('join_key')
        db_connection_id = request.form.get('db_connection_id')
        
        # Create new mapping
        new_mapping = MappingTable(
            name=name,
            source_table=source_table,
            destination_table=destination_table,
            join_key=join_key,
            db_connection_id=db_connection_id
        )
        
        db.session.add(new_mapping)
        db.session.commit()
        flash('Mapping added successfully', 'success')
        return redirect(url_for('mappings'))
    
    # GET request - show the form
    connections = DBConnection.query.all()
    return render_template('mappings.html', add_mode=True, connections=connections)

@app.route('/mappings/delete/<int:mapping_id>', methods=['POST'])
def delete_mapping(mapping_id):
    """Delete a mapping table configuration."""
    mapping = MappingTable.query.get_or_404(mapping_id)
    db.session.delete(mapping)
    db.session.commit()
    flash('Mapping deleted successfully', 'success')
    return redirect(url_for('mappings'))

@app.route('/process')
def process():
    """De-identification process page."""
    connections = DBConnection.query.all()
    rules = DeidentRule.query.all()
    mappings = MappingTable.query.all()
    return render_template('process.html', connections=connections, rules=rules, mappings=mappings)

@app.route('/process/execute', methods=['POST'])
def execute_process():
    """Execute the de-identification process."""
    # Get process parameters
    connection_id = request.form.get('connection_id')
    rule_ids = request.form.getlist('rule_ids')
    mapping_ids = request.form.getlist('mapping_ids')
    patient_table = request.form.get('patient_table')
    patient_id_field = request.form.get('patient_id_field')
    patient_id_format = request.form.get('patient_id_format', 'SW{:07d}')
    process_name = request.form.get('process_name', 'De-identification Process')
    
    # Validate inputs
    if not connection_id or not rule_ids:
        flash('Connection and at least one rule must be selected', 'danger')
        return redirect(url_for('process'))
    
    # Create process log
    process_log = ProcessLog(
        process_name=process_name,
        status='running'
    )
    db.session.add(process_log)
    db.session.commit()
    
    try:
        # Get database connection
        connection = DBConnection.query.get(connection_id)
        db_connector = DatabaseConnector.get_db_connection_from_model(connection)
        
        if not db_connector.connect():
            raise Exception("Could not connect to database")
        
        # Get selected rules
        selected_rules = DeidentRule.query.filter(DeidentRule.id.in_(rule_ids)).all()
        
        # Initialize the de-identifier
        deidentifier = Deidentifier(db_connector)
        deidentifier.load_rules(selected_rules)
        
        # Create master patient mapping if patient table is specified
        if patient_table and patient_id_field:
            deidentifier.create_master_patient_mapping(
                patient_table, 
                patient_id_field, 
                patient_id_format
            )
            
            # Apply master mapping to patient table
            deidentifier.apply_master_mapping(patient_table, patient_id_field)
        
        # Process mapping tables if selected
        if mapping_ids:
            selected_mappings = MappingTable.query.filter(MappingTable.id.in_(mapping_ids)).all()
            for mapping in selected_mappings:
                deidentifier.process_mapping_table(mapping)
        
        # Get tables and process each one
        tables = db_connector.get_tables()
        for table in tables:
            deidentifier.process_table(table)
        
        # Update process log with results
        stats = deidentifier.get_statistics()
        process_log.end_time = datetime.datetime.utcnow()
        process_log.status = 'completed'
        process_log.records_processed = stats['total_records']
        process_log.records_modified = stats['modified_records']
        process_log.log_data = json.dumps(stats)
        db.session.commit()
        
        # Generate report
        report_path = generate_report(process_log, stats)
        
        flash('De-identification process completed successfully', 'success')
        return redirect(url_for('results', process_id=process_log.id))
    
    except Exception as e:
        logger.error(f"Error in de-identification process: {str(e)}")
        
        # Update process log with error
        process_log.end_time = datetime.datetime.utcnow()
        process_log.status = 'failed'
        process_log.log_data = json.dumps({"error": str(e)})
        db.session.commit()
        
        flash(f'Error in de-identification process: {str(e)}', 'danger')
        return redirect(url_for('process'))

@app.route('/results/<int:process_id>')
def results(process_id):
    """Show results of a completed process."""
    process_log = ProcessLog.query.get_or_404(process_id)
    
    # Parse log data
    log_data = process_log.get_log_data()
    
    return render_template('results.html', process=process_log, log_data=log_data)

@app.route('/get-tables/<int:conn_id>')
def get_tables(conn_id):
    """AJAX endpoint to get tables for a connection."""
    connection = DBConnection.query.get_or_404(conn_id)
    
    try:
        connector = DatabaseConnector.get_db_connection_from_model(connection)
        if connector.connect():
            tables = connector.get_tables()
            connector.disconnect()
            return jsonify({
                'success': True,
                'tables': tables
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Could not connect to database'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/get-columns/<int:conn_id>/<table_name>')
def get_columns(conn_id, table_name):
    """AJAX endpoint to get columns for a table."""
    connection = DBConnection.query.get_or_404(conn_id)
    
    try:
        connector = DatabaseConnector.get_db_connection_from_model(connection)
        if connector.connect():
            columns = connector.get_columns(table_name)
            connector.disconnect()
            column_names = [col['name'] for col in columns]
            return jsonify({
                'success': True,
                'columns': column_names
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Could not connect to database'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

# Database Explorer routes
@app.route('/explorer')
def explorer():
    """Database explorer page."""
    connections = DBConnection.query.all()
    saved_queries = SavedQuery.query.all()
    return render_template('explorer.html', connections=connections, saved_queries=saved_queries)

@app.route('/api/explorer/structure/<int:conn_id>')
def explorer_structure(conn_id):
    """Get database structure for the explorer."""
    connection = DBConnection.query.get_or_404(conn_id)
    
    try:
        connector = DatabaseConnector.get_db_connection_from_model(connection)
        if connector.connect():
            # Get tables
            tables = []
            for table_name in connector.get_tables():
                columns = connector.get_columns(table_name)
                primary_keys = connector.get_primary_keys(table_name)
                
                # Transform columns to include primary key info
                formatted_columns = []
                for col in columns:
                    col_name = col['name'] if isinstance(col, dict) else col
                    formatted_columns.append({
                        'name': col_name,
                        'isPrimary': col_name in primary_keys,
                        'type': col.get('type', 'Unknown') if isinstance(col, dict) else 'Unknown'
                    })
                
                tables.append({
                    'name': table_name,
                    'columns': formatted_columns
                })
            
            connector.disconnect()
            return jsonify({
                'success': True,
                'database': connection.database,
                'tables': tables
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Could not connect to database'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/api/explorer/query', methods=['POST'])
def explorer_query():
    """Execute a query in the database explorer."""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'})
    
    connection_id = data.get('connection_id')
    query = data.get('query')
    limit_results = data.get('limit_results', True)
    
    if not connection_id or not query:
        return jsonify({'error': 'Missing connection_id or query'})
    
    # Get the connection
    connection = DBConnection.query.get_or_404(connection_id)
    
    # Execute the query
    try:
        connector = DatabaseConnector.get_db_connection_from_model(connection)
        if connector.connect():
            # Measure execution time
            start_time = time.time()
            
            # Append LIMIT if needed and not already present
            if limit_results and 'limit' not in query.lower():
                query = query + ' LIMIT 1000'
            
            # Execute the query
            df = connector.execute_query(query)
            execution_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
            
            # Disconnect
            connector.disconnect()
            
            # Convert DataFrame to dict for JSON response
            if df is not None and not df.empty:
                # Convert all values to string to avoid JSON serialization issues
                df = df.astype(str)
                
                # Return results
                return jsonify({
                    'success': True,
                    'columns': df.columns.tolist(),
                    'rows': df.to_dict('records'),
                    'execution_time': execution_time
                })
            else:
                return jsonify({
                    'success': True,
                    'columns': [],
                    'rows': [],
                    'execution_time': execution_time
                })
        else:
            return jsonify({'error': 'Could not connect to database'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/explorer/saved-query/<int:query_id>')
def get_saved_query(query_id):
    """Get a saved query."""
    query = SavedQuery.query.get_or_404(query_id)
    return jsonify({
        'success': True,
        'query': {
            'id': query.id,
            'name': query.name,
            'query_text': query.query_text,
            'db_connection_id': query.db_connection_id,
            'is_favorite': query.is_favorite
        }
    })

@app.route('/explorer/save-query', methods=['POST'])
def save_query():
    """Save a query."""
    query_name = request.form.get('query_name')
    query_text = request.form.get('query_text')
    connection_id = request.form.get('connection_id')
    is_favorite = 'is_favorite' in request.form
    
    if not query_name or not query_text or not connection_id:
        flash('All fields are required', 'danger')
        return redirect(url_for('explorer'))
    
    # Create new saved query
    new_query = SavedQuery(
        name=query_name,
        query_text=query_text,
        db_connection_id=connection_id,
        is_favorite=is_favorite
    )
    
    db.session.add(new_query)
    db.session.commit()
    
    flash('Query saved successfully', 'success')
    return redirect(url_for('explorer'))

# Master Module routes
@app.route('/master')
def master():
    """Master reference tables management page."""
    patient_masters = PatientMaster.query.all()
    encounter_masters = EncounterMaster.query.all()
    phi_masters = PHIAttributeMaster.query.all()
    # Get all database connections for dynamic table selection
    connections = DBConnection.query.all()
    
    return render_template('master.html', 
                          patient_masters=patient_masters,
                          encounter_masters=encounter_masters,
                          phi_masters=phi_masters,
                          connections=connections)

@app.route('/api/master/get-tables/<int:conn_id>', methods=['GET'])
def get_master_tables(conn_id):
    """Get tables from a database for master mapping."""
    connection = DBConnection.query.get_or_404(conn_id)
    
    try:
        connector = DatabaseConnector.get_db_connection_from_model(connection)
        if connector.connect():
            tables = connector.get_tables()
            connector.disconnect()
            return jsonify({
                'success': True,
                'tables': tables
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Could not connect to database'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/master/get-columns/<int:conn_id>/<string:table_name>', methods=['GET'])
def get_master_columns(conn_id, table_name):
    """Get columns from a table for master mapping."""
    connection = DBConnection.query.get_or_404(conn_id)
    
    try:
        connector = DatabaseConnector.get_db_connection_from_model(connection)
        if connector.connect():
            columns = connector.get_columns(table_name)
            connector.disconnect()
            return jsonify({
                'success': True,
                'columns': columns
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Could not connect to database'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/master/patient/add', methods=['POST'])
def add_patient_master():
    """Add a new patient master record or create a dynamic master mapping."""
    # Check if this is a dynamic mapping request
    if 'db_connection_id' in request.form and 'table_name' in request.form and 'id_column' in request.form:
        # This is a dynamic mapping request
        db_connection_id = request.form.get('db_connection_id')
        table_name = request.form.get('table_name')
        id_column = request.form.get('id_column')
        
        # Get database connection
        connection = DBConnection.query.get_or_404(db_connection_id)
        connector = DatabaseConnector.get_db_connection_from_model(connection)
        
        if connector.connect():
            try:
                # Get all IDs from the specified table
                query = f"SELECT {id_column} FROM {table_name}"
                df = connector.execute_query(query)
                connector.disconnect()
                
                if not df.empty:
                    # Generate a mapping for each ID
                    # Get the highest existing ID to start incrementing from
                    highest_id = 0
                    existing_id = db.session.query(func.max(PatientMaster.deidentified_id)).first()[0]
                    if existing_id:
                        try:
                            highest_id = int(existing_id.replace("SW", ""))
                        except:
                            highest_id = 0
                    
                    # Add each ID to master mapping
                    count = 0
                    for idx, row in df.iterrows():
                        orig_id = str(row[id_column])
                        
                        # Skip if this ID already exists
                        existing = PatientMaster.query.filter_by(original_patient_id=orig_id).first()
                        if existing:
                            continue
                        
                        # Create new deidentified ID
                        highest_id += 1
                        new_deid = f"SW{highest_id:07d}"
                        
                        # Generate random date offset within -32 to +32 days
                        random_offset = random.randint(-32, 32)
                        
                        # Create new mapping
                        new_patient = PatientMaster(
                            original_patient_id=orig_id,
                            deidentified_id=new_deid,
                            date_offset=random_offset
                        )
                        
                        db.session.add(new_patient)
                        count += 1
                    
                    db.session.commit()
                    flash(f'Created {count} mappings for patient IDs from {table_name}', 'success')
                else:
                    flash(f'No data found in table {table_name}', 'warning')
            except Exception as e:
                flash(f'Error creating mappings: {str(e)}', 'danger')
                db.session.rollback()
        else:
            flash('Could not connect to database', 'danger')
            
        return redirect(url_for('master'))
    
    # Regular manual mapping
    original_patient_id = request.form.get('original_patient_id')
    deidentified_id = "SW" + request.form.get('deidentified_id', '0000001').zfill(7)
    date_offset = int(request.form.get('date_offset', '0'))
    
    # Check if original_patient_id already exists
    existing = PatientMaster.query.filter_by(original_patient_id=original_patient_id).first()
    if existing:
        flash('A mapping for this patient ID already exists', 'warning')
        return redirect(url_for('master'))
    
    # Check if deidentified_id already exists
    existing = PatientMaster.query.filter_by(deidentified_id=deidentified_id).first()
    if existing:
        flash('This de-identified ID is already in use', 'warning')
        return redirect(url_for('master'))
    
    # Create new patient master
    new_patient = PatientMaster(
        original_patient_id=original_patient_id,
        deidentified_id=deidentified_id,
        date_offset=date_offset
    )
    
    db.session.add(new_patient)
    db.session.commit()
    
    flash('Patient master record added successfully', 'success')
    return redirect(url_for('master'))

@app.route('/master/patient/edit/<int:patient_id>', methods=['POST'])
def edit_patient_master(patient_id):
    """Edit a patient master record."""
    patient = PatientMaster.query.get_or_404(patient_id)
    
    patient.original_patient_id = request.form.get('original_patient_id')
    patient.deidentified_id = "SW" + request.form.get('deidentified_id', '0000001')
    patient.date_offset = int(request.form.get('date_offset', '0'))
    
    db.session.commit()
    
    flash('Patient master record updated successfully', 'success')
    return redirect(url_for('master'))

@app.route('/master/patient/delete/<int:patient_id>', methods=['POST'])
def delete_patient_master(patient_id):
    """Delete a patient master record."""
    patient = PatientMaster.query.get_or_404(patient_id)
    
    # Check if this patient has related records
    encounter_count = EncounterMaster.query.filter_by(patient_master_id=patient_id).count()
    phi_count = PHIAttributeMaster.query.filter_by(patient_master_id=patient_id).count()
    
    if encounter_count > 0 or phi_count > 0:
        flash('Cannot delete this patient because it has related encounter or PHI records', 'danger')
        return redirect(url_for('master'))
    
    db.session.delete(patient)
    db.session.commit()
    
    flash('Patient master record deleted successfully', 'success')
    return redirect(url_for('master'))

@app.route('/master/encounter/add', methods=['POST'])
def add_encounter_master():
    """Add a new encounter master record or create dynamic encounter mappings."""
    patient_master_id = request.form.get('patient_master_id')
    
    # Check if this is a dynamic mapping request
    if 'db_connection_id' in request.form and 'table_name' in request.form and 'id_column' in request.form:
        # This is a dynamic mapping request
        db_connection_id = request.form.get('db_connection_id')
        table_name = request.form.get('table_name')
        id_column = request.form.get('id_column')
        
        # Get database connection
        connection = DBConnection.query.get_or_404(db_connection_id)
        connector = DatabaseConnector.get_db_connection_from_model(connection)
        
        if connector.connect():
            try:
                # Get all IDs from the specified table
                query = f"SELECT {id_column} FROM {table_name}"
                df = connector.execute_query(query)
                connector.disconnect()
                
                if not df.empty:
                    # Get the patient record
                    patient = PatientMaster.query.get_or_404(patient_master_id)
                    
                    # Generate a mapping for each encounter ID
                    # Get the highest existing ID to start incrementing from
                    highest_id = 0
                    existing_id = db.session.query(func.max(EncounterMaster.deidentified_id)).first()[0]
                    if existing_id:
                        try:
                            highest_id = int(existing_id.replace("SW", ""))
                        except:
                            highest_id = 0
                    
                    # Add each ID to master mapping
                    count = 0
                    for idx, row in df.iterrows():
                        orig_id = str(row[id_column])
                        
                        # Skip if this ID already exists
                        existing = EncounterMaster.query.filter_by(original_encounter_id=orig_id).first()
                        if existing:
                            continue
                        
                        # Create new deidentified ID - 10 digit format for encounters
                        highest_id += 1
                        new_deid = f"SW{highest_id:010d}"
                        
                        # Create new mapping
                        new_encounter = EncounterMaster(
                            original_encounter_id=orig_id,
                            deidentified_id=new_deid,
                            patient_master_id=patient_master_id
                        )
                        
                        db.session.add(new_encounter)
                        count += 1
                    
                    db.session.commit()
                    flash(f'Created {count} mappings for encounter IDs from {table_name}', 'success')
                else:
                    flash('No IDs found in the selected table', 'warning')
            except Exception as e:
                flash(f'Error processing encounter IDs: {str(e)}', 'danger')
                logging.error(f"Error in dynamic encounter mapping: {str(e)}")
        else:
            flash('Could not connect to database', 'danger')
        
        return redirect(url_for('master'))
    
    # Handle single encounter mapping
    original_encounter_id = request.form.get('original_encounter_id')
    deidentified_id = "SW" + request.form.get('deidentified_id', '0000010001')
    
    # Check if original_encounter_id already exists
    existing = EncounterMaster.query.filter_by(original_encounter_id=original_encounter_id).first()
    if existing:
        flash('A mapping for this encounter ID already exists', 'warning')
        return redirect(url_for('master'))
    
    # Check if deidentified_id already exists
    existing = EncounterMaster.query.filter_by(deidentified_id=deidentified_id).first()
    if existing:
        flash('This de-identified ID is already in use', 'warning')
        return redirect(url_for('master'))
    
    # Create new encounter master
    new_encounter = EncounterMaster(
        original_encounter_id=original_encounter_id,
        deidentified_id=deidentified_id,
        patient_master_id=patient_master_id
    )
    
    db.session.add(new_encounter)
    db.session.commit()
    
    flash('Encounter master record added successfully', 'success')
    return redirect(url_for('master'))

@app.route('/master/encounter/edit/<int:encounter_id>', methods=['POST'])
def edit_encounter_master(encounter_id):
    """Edit an encounter master record."""
    encounter = EncounterMaster.query.get_or_404(encounter_id)
    
    encounter.original_encounter_id = request.form.get('original_encounter_id')
    encounter.deidentified_id = "SW" + request.form.get('deidentified_id', '0000010001')
    encounter.patient_master_id = request.form.get('patient_master_id')
    
    db.session.commit()
    
    flash('Encounter master record updated successfully', 'success')
    return redirect(url_for('master'))

@app.route('/master/encounter/delete/<int:encounter_id>', methods=['POST'])
def delete_encounter_master(encounter_id):
    """Delete an encounter master record."""
    encounter = EncounterMaster.query.get_or_404(encounter_id)
    
    db.session.delete(encounter)
    db.session.commit()
    
    flash('Encounter master record deleted successfully', 'success')
    return redirect(url_for('master'))

@app.route('/master/phi/add', methods=['POST'])
def add_phi_master():
    """Add a new PHI attribute master record."""
    patient_master_id = request.form.get('patient_master_id')
    attribute_name = request.form.get('attribute_name')
    original_value = request.form.get('original_value')
    deidentified_value = request.form.get('deidentified_value')
    
    # Handle custom attribute
    if attribute_name == 'CUSTOM':
        attribute_name = request.form.get('custom_attribute')
    
    # Create new PHI attribute
    new_phi = PHIAttributeMaster(
        patient_master_id=patient_master_id,
        attribute_name=attribute_name,
        original_value=original_value,
        deidentified_value=deidentified_value
    )
    
    db.session.add(new_phi)
    db.session.commit()
    
    flash('PHI attribute record added successfully', 'success')
    return redirect(url_for('master'))

@app.route('/master/phi/edit/<int:phi_id>', methods=['POST'])
def edit_phi_master(phi_id):
    """Edit a PHI attribute master record."""
    phi = PHIAttributeMaster.query.get_or_404(phi_id)
    
    phi.patient_master_id = request.form.get('patient_master_id')
    phi.attribute_name = request.form.get('attribute_name')
    if phi.attribute_name == 'CUSTOM':
        phi.attribute_name = request.form.get('custom_attribute')
    phi.original_value = request.form.get('original_value')
    phi.deidentified_value = request.form.get('deidentified_value')
    
    db.session.commit()
    
    flash('PHI attribute record updated successfully', 'success')
    return redirect(url_for('master'))

@app.route('/master/phi/delete/<int:phi_id>', methods=['POST'])
def delete_phi_master(phi_id):
    """Delete a PHI attribute master record."""
    phi = PHIAttributeMaster.query.get_or_404(phi_id)
    
    db.session.delete(phi)
    db.session.commit()
    
    flash('PHI attribute record deleted successfully', 'success')
    return redirect(url_for('master'))

# Add these routes after the existing routes

@app.route('/api/phi/analyze', methods=['POST'])
def analyze_phi():
    """Analyze PHI content in database tables."""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'})

    connection_id = data.get('connection_id')
    table_name = data.get('table_name')
    selected_columns = data.get('columns', [])
    detection_mode = data.get('detection_mode', 'pattern')

    if not connection_id or not table_name:
        return jsonify({'error': 'Missing connection_id or table_name'})

    # Get the connection
    connection = DBConnection.query.get_or_404(connection_id)

    try:
        # Initialize services
        connector = DatabaseConnector.get_db_connection_from_model(connection)
        phi_service = PHIService()

        # Analyze the table
        analysis_results = phi_service.analyze_database_columns(
            connection=connector,
            table_name=table_name,
            selected_columns=selected_columns,
            detection_mode=detection_mode
        )

        if 'error' in analysis_results:
            return jsonify({'error': analysis_results['error']})

        return jsonify({
            'success': True,
            'analysis': analysis_results
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/phi/suggest-plan', methods=['POST'])
def suggest_deidentification_plan():
    """Generate a de-identification plan based on PHI analysis."""
    data = request.json
    if not data or 'analysis' not in data:
        return jsonify({'error': 'No analysis data provided'})
    
    try:
        phi_service = PHIService()
        plan = phi_service.suggest_deidentification_plan(data['analysis'])
        
        return jsonify({
            'success': True,
            'plan': plan
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/phi/execute-plan', methods=['POST'])
def execute_deidentification():
    """Execute a de-identification plan."""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'})
    
    connection_id = data.get('connection_id')
    plan = data.get('plan')
    target_schema = data.get('target_schema', 'deidentified')
    
    if not connection_id or not plan:
        return jsonify({'error': 'Missing connection_id or plan'})
    
    # Get the connection
    connection = DBConnection.query.get_or_404(connection_id)
    
    try:
        # Initialize services
        connector = DatabaseConnector.get_db_connection_from_model(connection)
        phi_service = PHIService()
        
        # Execute the plan
        results = phi_service.execute_deidentification(connector, plan, target_schema)
        
        if results.get('status') == 'error':
            return jsonify({'error': results['error']})
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/phi-detection')
def phi_detection():
    """PHI detection and de-identification page."""
    connections = DBConnection.query.all()
    return render_template('phi_detection.html', connections=connections)