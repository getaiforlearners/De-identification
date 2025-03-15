# NoTraceHealth - Healthcare Data De-identification System

## Overview
NoTraceHealth is a comprehensive Flask-based healthcare data processing application specializing in advanced de-identification and privacy protection technologies. The system combines pattern-based and AI-powered detection methods to identify and secure Protected Health Information (PHI) in healthcare databases.

## Key Features
- Advanced PHI Detection using pattern matching and Google Cloud NLP
- Multiple database connector support (PostgreSQL, MySQL, SQL Server, Oracle, SQLite)
- Flexible database exploration with resizable interfaces
- AI-powered data transformation capabilities
- Secure data handling with staging database support
- HIPAA compliance-focused data processing

## Architecture

### Core Components
1. **PHI Detection Engine**
   - Pattern-based detection (`phi_detector.py`)
   - AI-powered detection (`ai_service.py`)
   - Service orchestration (`phi_service.py`)

2. **Database Management**
   - Multi-database support (`db_connector.py`)
   - Connection management
   - Query execution and data transformation

3. **Web Interface**
   - Flask-based web application
   - Interactive PHI analysis dashboard
   - De-identification workflow
   - Database exploration tools

## Installation and Setup

### Prerequisites
```bash
# System Requirements
- Python 3.11 or higher
- PostgreSQL database
- Google Cloud API access
```

### Environment Variables
```bash
# Required environment variables
DATABASE_URL="postgresql://user:password@host:port/dbname"
GOOGLE_API_KEY="your-google-api-key"
SESSION_SECRET="your-session-secret"
```

### Dependencies Installation
```bash
# Install required Python packages
pip install -r requirements.txt

# Key dependencies:
- Flask
- SQLAlchemy
- google-cloud-language
- psycopg2-binary
- mysql-connector-python
- cx_Oracle
- pandas
- numpy
```

## Module Documentation

### 1. PHI Detection Module (`phi_detector.py`)
```python
from phi_detector import PHIDetector

# Initialize detector
detector = PHIDetector()

# Detect PHI in text
findings = detector.detect_phi("Patient John Doe (DOB: 01/15/1980)")

# Analyze database column
results = detector.analyze_database_column(
    column_name="patient_notes",
    sample_data=["Sample medical text..."]
)
```

### 2. AI Service Module (`ai_service.py`)
```python
from ai_service import AIPhiDetector

# Initialize AI detector
ai_detector = AIPhiDetector()

# Analyze medical text
results = ai_detector.analyze_medical_text(
    "Patient presented to Dr. Smith with chest pain"
)
```

### 3. Database Connector Module (`db_connector.py`)
```python
from db_connector import DatabaseConnector

# Initialize connector
connector = DatabaseConnector(
    db_type='postgresql',
    host='localhost',
    port=5432,
    database='healthcare_db',
    username='user',
    password='pass'
)

# Execute query
results = connector.execute_query(
    "SELECT * FROM patients LIMIT 10"
)
```

## API Endpoints

### PHI Detection and De-identification
1. **Analyze PHI Content**
   ```http
   POST /api/phi/analyze
   Content-Type: application/json
   
   {
       "connection_id": "123",
       "table_name": "patients"
   }
   ```

2. **Generate De-identification Plan**
   ```http
   POST /api/phi/suggest-plan
   Content-Type: application/json
   
   {
       "analysis": {
           "table_name": "patients",
           "columns": [...]
       }
   }
   ```

3. **Execute De-identification**
   ```http
   POST /api/phi/execute-plan
   Content-Type: application/json
   
   {
       "connection_id": "123",
       "plan": {...},
       "target_schema": "deidentified"
   }
   ```

## Google Cloud NLP Integration

### Setup
1. Obtain Google Cloud API key from Google Cloud Console
2. Enable Natural Language API
3. Set GOOGLE_API_KEY environment variable
4. Verify integration:
   ```python
   from ai_service import AIPhiDetector
   detector = AIPhiDetector()
   ```

### Features
- Entity recognition for medical terms
- Context-aware PHI detection
- Confidence scoring
- Medical terminology recognition

### Example Usage
```python
# Initialize AI detector
ai_detector = AIPhiDetector()

# Analyze medical text
text = """
Patient was seen by Dr. Sarah Johnson at 
Memorial Hospital on March 15, 2025. 
Contact: (555) 123-4567
"""

analysis = ai_detector.analyze_medical_text(text)
print(f"Found {len(analysis['findings'])} PHI elements")
```

## Security Considerations

### Data Protection
- PHI is never stored permanently
- All sensitive data is handled securely
- De-identified data is stored in separate schemas
- API keys and credentials are stored as environment variables

### Best Practices
1. Regular security audits
2. Access control implementation
3. Data encryption in transit and at rest
4. Regular backup procedures

## Testing and Validation

### PHI Detection Testing
```python
# Test pattern-based detection
detector = PHIDetector()
test_text = "SSN: 123-45-6789, DOB: 01/15/1980"
findings = detector.detect_phi(test_text)

# Test AI-powered detection
ai_detector = AIPhiDetector()
medical_text = "Patient seen by Dr. Smith"
ai_findings = ai_detector.analyze_medical_text(medical_text)
```

### Database Integration Testing
```python
# Test database connection
connector = DatabaseConnector(...)
assert connector.connect()

# Test query execution
results = connector.execute_query("SELECT 1")
assert not results.empty
```

## Troubleshooting

### Common Issues
1. Database Connection Issues
   - Verify connection parameters
   - Check database permissions
   - Ensure proper network access

2. AI Detection Issues
   - Verify Google API key
   - Check API quotas and limits
   - Review error logs

3. PHI Detection Accuracy
   - Adjust confidence thresholds
   - Update pattern definitions
   - Verify AI service status

## Contributing
1. Follow PEP 8 style guide
2. Add appropriate documentation
3. Include unit tests
4. Submit pull requests for review

## License
[License information goes here]
