# NoTraceHealth Setup Guide

## Environment Setup

1. Install Required Dependencies
```bash
pip install -r requirements.txt
```

2. Set Environment Variables
```bash
# Database Configuration
export DATABASE_URL="postgresql://user:password@host:port/dbname"

# Google Cloud API (for enhanced PHI detection)
export GOOGLE_API_KEY="your-api-key"

# Flask Session Secret
export SESSION_SECRET="your-secret-key"
```

## Module Overview

### 1. Database Module
- Location: `db_connector.py`
- Purpose: Database connection management
- Supported Databases:
  - PostgreSQL
  - MySQL
  - SQL Server
  - Oracle
  - SQLite

### 2. PHI Detection Module
- Location: `phi_detector.py`, `ai_service.py`
- Features:
  - Pattern-based PHI detection
  - AI-powered analysis
  - De-identification planning
  - Medical context analysis

### 3. Web Interface
- Location: `templates/`
- Features:
  - Database exploration
  - PHI analysis dashboard
  - De-identification workflow
  - Result visualization

## Quick Start

1. Start the Application
```bash
python main.py
```

2. Access the Web Interface
- Open browser at `http://localhost:5000`
- Navigate to "Connections" to set up database
- Use "PHI Detection" for analysis

## Configuration Options

### Database Connection
```python
from db_connector import DatabaseConnector

# Example: PostgreSQL
connector = DatabaseConnector(
    db_type='postgresql',
    host='localhost',
    port=5432,
    database='healthcare_db',
    username='user',
    password='pass'
)
```

### PHI Detection
```python
from phi_detector import PHIDetector

detector = PHIDetector()
# AI detection automatically enabled if GOOGLE_API_KEY is set
```

## Troubleshooting

### Common Issues

1. Database Connection
- Verify connection parameters
- Check database permissions
- Ensure proper network access

2. PHI Detection
- Verify API key is set
- Check for supported data types
- Review detection patterns

3. Web Interface
- Clear browser cache
- Check port availability
- Verify Flask server status

### Getting Help
- Check the logs in `flask.log`
- Review error messages in browser console
- Consult documentation in `docs/`
