from app import db
from datetime import datetime
import json

class DBConnection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    db_type = db.Column(db.String(50), nullable=False)  # mysql, postgresql, sqlserver, oracle, sqlite
    host = db.Column(db.String(100), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    database = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    extra_params = db.Column(db.Text, nullable=True)  # JSON field for additional parameters
    is_destination = db.Column(db.Boolean, default=False)  # Flag to mark as destination DB
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<DBConnection {self.name} - {self.db_type}>"

class DeidentRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    rule_type = db.Column(db.String(50), nullable=False)  # patient_id, date, text, email, phone, etc.
    config = db.Column(db.Text, nullable=False)  # JSON configuration for the rule
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<DeidentRule {self.name} - {self.rule_type}>"
    
    def get_config(self):
        return json.loads(self.config)

class MappingTable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    source_table = db.Column(db.String(100), nullable=False)
    destination_table = db.Column(db.String(100), nullable=False)
    join_key = db.Column(db.String(100), nullable=False)
    db_connection_id = db.Column(db.Integer, db.ForeignKey('db_connection.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    db_connection = db.relationship('DBConnection', backref=db.backref('mappings', lazy=True))
    
    def __repr__(self):
        return f"<MappingTable {self.name}: {self.source_table} -> {self.destination_table}>"

# Master Module Tables
class PatientMaster(db.Model):
    """Master table for patient identifiers"""
    id = db.Column(db.Integer, primary_key=True)
    original_patient_id = db.Column(db.String(100), nullable=False, unique=True)
    deidentified_id = db.Column(db.String(100), nullable=False)  # Format: SW0000001
    date_offset = db.Column(db.Integer, nullable=False)  # Days to offset dates (-32 to +32)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PatientMaster {self.original_patient_id} -> {self.deidentified_id}>"

class EncounterMaster(db.Model):
    """Master table for encounter identifiers"""
    id = db.Column(db.Integer, primary_key=True)
    original_encounter_id = db.Column(db.String(100), nullable=False, unique=True)
    deidentified_id = db.Column(db.String(100), nullable=False)  # Format: SW0000010001
    patient_master_id = db.Column(db.Integer, db.ForeignKey('patient_master.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    patient = db.relationship('PatientMaster', backref=db.backref('encounters', lazy=True))
    
    def __repr__(self):
        return f"<EncounterMaster {self.original_encounter_id} -> {self.deidentified_id}>"

class PHIAttributeMaster(db.Model):
    """Master table for PHI attributes (SSN, phone, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    patient_master_id = db.Column(db.Integer, db.ForeignKey('patient_master.id'), nullable=False)
    attribute_name = db.Column(db.String(100), nullable=False)  # SSN, phone, email, etc.
    original_value = db.Column(db.String(255), nullable=False)
    deidentified_value = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    patient = db.relationship('PatientMaster', backref=db.backref('phi_attributes', lazy=True))
    
    def __repr__(self):
        return f"<PHIAttributeMaster {self.attribute_name}: {self.original_value} -> {self.deidentified_value}>"

class SavedQuery(db.Model):
    """Model for storing saved SQL queries"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    db_connection_id = db.Column(db.Integer, db.ForeignKey('db_connection.id'), nullable=False)
    query_text = db.Column(db.Text, nullable=False)
    is_favorite = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    db_connection = db.relationship('DBConnection', backref=db.backref('saved_queries', lazy=True))
    
    def __repr__(self):
        return f"<SavedQuery {self.name}>"

class ProcessLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    process_name = db.Column(db.String(100), nullable=False)
    source_connection_id = db.Column(db.Integer, db.ForeignKey('db_connection.id'), nullable=False)
    destination_connection_id = db.Column(db.Integer, db.ForeignKey('db_connection.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="running")  # running, completed, failed
    records_processed = db.Column(db.Integer, default=0)
    records_modified = db.Column(db.Integer, default=0)
    log_data = db.Column(db.Text, nullable=True)  # JSON log data
    
    # Relationships
    source_connection = db.relationship('DBConnection', foreign_keys=[source_connection_id])
    destination_connection = db.relationship('DBConnection', foreign_keys=[destination_connection_id])
    
    def __repr__(self):
        return f"<ProcessLog {self.process_name} - {self.status}>"
    
    def get_log_data(self):
        if self.log_data:
            return json.loads(self.log_data)
        return {}
    
    def set_log_data(self, data):
        self.log_data = json.dumps(data)