import pandas as pd
import numpy as np
import logging
import random
import re
import datetime
import hashlib
import uuid
from db_connector import DatabaseConnector
from rule_engine import RuleEngine

logger = logging.getLogger(__name__)

class Deidentifier:
    """
    Main class for the de-identification process. Connects to the source database,
    retrieves data, applies de-identification rules, and stores the de-identified
    data in the target location.
    """
    def __init__(self, db_connection, rules=None):
        """Initialize with database connection and rules."""
        self.db_connection = db_connection
        self.rules = rules or []
        self.rule_engine = RuleEngine()
        self.master_mapping = {}
        self.mappings = {}
        self.stats = {
            'total_records': 0,
            'modified_records': 0,
            'tables_processed': 0,
            'fields_modified': {}
        }
    
    def load_rules(self, rules):
        """Load de-identification rules."""
        self.rules = rules
        self.rule_engine.load_rules(rules)
        logger.info(f"Loaded {len(rules)} de-identification rules")
    
    def process_table(self, table_name, primary_key=None):
        """Process a single table for de-identification."""
        logger.info(f"Processing table: {table_name}")
        
        # Get the primary key if not provided
        if not primary_key:
            pk_columns = self.db_connection.get_primary_keys(table_name)
            if pk_columns:
                primary_key = pk_columns[0]
            else:
                logger.warning(f"No primary key found for table {table_name}, using index as key")
                primary_key = None
        
        # Get table columns
        columns = self.db_connection.get_columns(table_name)
        column_names = [col['name'] for col in columns]
        
        # Fetch data from the table
        query = f"SELECT * FROM {table_name}"
        df = self.db_connection.execute_query(query)
        
        if df.empty:
            logger.warning(f"No data found in table {table_name}")
            return False
        
        # Update statistics
        self.stats['total_records'] += len(df)
        self.stats['tables_processed'] += 1
        
        # Process each column based on rules
        modified = False
        for column in column_names:
            if column not in df.columns:
                continue
                
            # Apply rules to this column
            column_modified = self._apply_rules_to_column(df, table_name, column)
            if column_modified:
                modified = True
                
                # Update column statistics
                if column not in self.stats['fields_modified']:
                    self.stats['fields_modified'][column] = 0
                self.stats['fields_modified'][column] += df[column].notna().sum()
        
        if modified:
            # Update the modified records count
            self.stats['modified_records'] += len(df)
            
            # Store the modified data back to the database
            # For demo purposes, we're not actually writing back to the original database
            # Instead, you could write to a new table or export to a file
            logger.info(f"Processed and de-identified {len(df)} records in table {table_name}")
            return True
        
        logger.info(f"No modifications needed for table {table_name}")
        return False
    
    def _apply_rules_to_column(self, df, table_name, column_name):
        """Apply de-identification rules to a specific column."""
        modified = False
        
        for rule in self.rules:
            # Check if the rule applies to this column
            if self.rule_engine.column_matches_rule(table_name, column_name, rule):
                # Apply the rule transformation
                df[column_name] = self.rule_engine.apply_rule(df[column_name], rule)
                modified = True
                logger.debug(f"Applied rule '{rule.name}' to {table_name}.{column_name}")
        
        return modified
    
    def process_mapping_table(self, mapping_config):
        """Process a mapping table that links tables together."""
        source_table = mapping_config.source_table
        dest_table = mapping_config.destination_table
        join_key = mapping_config.join_key
        
        logger.info(f"Processing mapping from {source_table} to {dest_table} on key {join_key}")
        
        # Get data from source table
        source_query = f"SELECT * FROM {source_table}"
        source_df = self.db_connection.execute_query(source_query)
        
        if source_df.empty:
            logger.warning(f"No data found in source table {source_table}")
            return False
        
        # Get data from destination table
        dest_query = f"SELECT * FROM {dest_table}"
        dest_df = self.db_connection.execute_query(dest_query)
        
        if dest_df.empty:
            logger.warning(f"No data found in destination table {dest_table}")
            return False
        
        # Create mapping between the tables
        mapping = {}
        for idx, row in source_df.iterrows():
            if join_key in row and row[join_key] is not None:
                source_key = str(row[join_key])
                
                # Find matching records in destination table
                matches = dest_df[dest_df[join_key] == source_key]
                
                for _, match_row in matches.iterrows():
                    dest_key = str(match_row[join_key])
                    mapping[source_key] = dest_key
        
        self.mappings[f"{source_table}_{dest_table}"] = mapping
        logger.info(f"Created mapping with {len(mapping)} entries between {source_table} and {dest_table}")
        return True
    
    def create_master_patient_mapping(self, patient_table, id_field, id_format="SW{:07d}"):
        """Create a master mapping for patient IDs."""
        logger.info(f"Creating master patient ID mapping from table {patient_table}")
        
        # Get all patient IDs
        query = f"SELECT DISTINCT {id_field} FROM {patient_table}"
        df = self.db_connection.execute_query(query)
        
        if df.empty:
            logger.warning(f"No patient IDs found in table {patient_table}")
            return False
        
        # Create mapping with custom format
        mapping = {}
        for i, row in df.iterrows():
            original_id = str(row[id_field])
            new_id = id_format.format(i + 1)  # Start from 1
            mapping[original_id] = new_id
        
        self.master_mapping = mapping
        logger.info(f"Created master patient mapping with {len(mapping)} entries")
        return True
    
    def get_statistics(self):
        """Get statistics about the de-identification process."""
        return self.stats
    
    def apply_master_mapping(self, table_name, id_field):
        """Apply the master patient mapping to a table."""
        if not self.master_mapping:
            logger.warning("No master mapping available. Create it first.")
            return False
        
        query = f"SELECT * FROM {table_name}"
        df = self.db_connection.execute_query(query)
        
        if df.empty:
            logger.warning(f"No data found in table {table_name}")
            return False
        
        # Apply mapping
        if id_field in df.columns:
            df[id_field] = df[id_field].astype(str).map(self.master_mapping)
            
            # Update statistics
            self.stats['total_records'] += len(df)
            self.stats['modified_records'] += len(df)
            self.stats['tables_processed'] += 1
            
            if id_field not in self.stats['fields_modified']:
                self.stats['fields_modified'][id_field] = 0
            self.stats['fields_modified'][id_field] += df[id_field].notna().sum()
            
            logger.info(f"Applied master mapping to {len(df)} records in {table_name}.{id_field}")
            return True
        
        logger.warning(f"Field {id_field} not found in table {table_name}")
        return False
    
    def export_master_mapping(self, file_path):
        """Export the master mapping to a file for reference."""
        if not self.master_mapping:
            logger.warning("No master mapping available to export")
            return False
        
        try:
            mapping_df = pd.DataFrame(list(self.master_mapping.items()), 
                                     columns=['original_id', 'deidentified_id'])
            mapping_df.to_csv(file_path, index=False)
            logger.info(f"Master mapping exported to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting master mapping: {str(e)}")
            return False
