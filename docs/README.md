# NoTraceHealth: Healthcare Data De-Identification System

## Overview
NoTraceHealth is a comprehensive Flask-based healthcare data processing application specializing in advanced de-identification and privacy protection technologies. It provides robust capabilities for detecting and managing Protected Health Information (PHI) in healthcare databases.

## Key Features
- Advanced PHI Detection using pattern matching and AI
- Flexible database exploration with resizable interfaces
- AI-powered data transformation capabilities
- Secure data handling with staging database support
- HIPAA compliance-focused data processing

## Installation

### Prerequisites
- Python 3.11 or higher
- PostgreSQL database
- Required system dependencies

### Dependencies Installation
```bash
# Install required Python packages
pip install -r requirements.txt
```

Required packages:
- Flask
- SQLAlchemy
- psycopg2-binary
- google-cloud-language
- pandas
- numpy

## Module Overview

### 1. PHI Detection Module
- Location: `phi_detector.py`
- Purpose: Core PHI detection using pattern matching and AI
- Features:
  - Pattern-based PHI detection
  - AI-powered unstructured text analysis
  - Confidence scoring
  - Context-aware detection

### 2. Database Connector Module
- Location: `db_connector.py`
- Purpose: Handle database connections and operations
- Supported Databases:
  - PostgreSQL
  - MySQL
  - SQL Server
  - Oracle
  - SQLite

### 3. AI Service Module
- Location: `ai_service.py`
- Purpose: Enhanced PHI detection using Google Cloud NLP
- Features:
  - Medical context analysis
  - Entity detection
  - Confidence scoring
  - Medical terminology recognition

### 4. PHI Service Module
- Location: `phi_service.py`
- Purpose: Orchestrate PHI detection and de-identification
- Features:
  - Database column analysis
  - De-identification planning
  - Execution of de-identification plans

## Configuration

### Environment Variables
Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `GOOGLE_API_KEY`: Google Cloud API key for AI detection
- `SESSION_SECRET`: Flask session secret key

### Database Setup
The application automatically creates necessary tables on startup using SQLAlchemy models.

## Usage

### Starting the Application
```bash
python main.py
```
The application will be available at `http://localhost:5000`

### Database Connection
1. Navigate to Connections page
2. Add new database connection
3. Provide connection details
4. Test connection

### PHI Detection
1. Select database and table
2. Run PHI analysis
3. Review detected PHI
4. Generate de-identification plan
5. Execute plan

## Security Considerations
- All sensitive data is handled securely
- PHI is never stored permanently
- De-identified data is stored in separate schemas
- API keys and credentials are stored as environment variables

## Troubleshooting
Common issues and solutions:
1. Database Connection Issues
   - Verify connection parameters
   - Check database permissions
   - Ensure proper network access

2. AI Detection Issues
   - Verify Google API key
   - Check API quotas and limits
   - Review error logs

## Contributing
Guidelines for contributing to the project:
1. Follow PEP 8 style guide
2. Add appropriate documentation
3. Include unit tests
4. Submit pull requests for review

## License
[License information goes here]
