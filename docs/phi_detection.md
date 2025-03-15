# PHI Detection Module Documentation

## Overview
The PHI Detection module combines pattern-based detection with AI-powered analysis using Google Cloud Natural Language API to identify Protected Health Information (PHI) in healthcare data.

## Components

### 1. Pattern-Based Detection
- Implementation: `phi_detector.py`
- Capabilities:
  - Patient IDs and Medical Record Numbers
  - Social Security Numbers
  - Contact Information (Phone, Email)
  - Dates and Age Information
  - Provider and Facility IDs
  - Names and Credentials
  - Addresses and ZIP Codes

### 2. AI-Powered Detection
- Implementation: `ai_service.py`
- Features:
  - Natural Language Processing via Google Cloud API
  - Medical Context Analysis
  - Entity Recognition
  - Confidence Scoring
  - Unstructured Text Analysis

## Setup

### Prerequisites
1. Google Cloud API Key
   ```bash
   export GOOGLE_API_KEY='your-api-key'
   ```

2. Required Python Packages
   ```
   google-cloud-language
   ```

### Configuration
The AI detection service automatically initializes when the PHI detector is created. If the Google API key is not available, the system falls back to pattern-based detection only.

## Usage

### Basic PHI Detection
```python
from phi_detector import PHIDetector

detector = PHIDetector()
text = "Patient John Doe (DOB: 01/15/1980) was prescribed..."
findings = detector.detect_phi(text)
```

### Database Column Analysis
```python
results = detector.analyze_database_column(
    column_name="patient_notes",
    sample_data=["Sample medical text..."]
)
```

### De-identification Planning
```python
suggestions = detector.suggest_deidentification(
    findings,
    column_name="medical_notes"
)
```

## AI Detection Details

### Entity Types
The AI service maps Google Cloud entity types to PHI categories:
- PERSON → name
- LOCATION → address
- ORGANIZATION → facility_id
- DATE → date
- PHONE_NUMBER → phone
- ADDRESS → address

### Confidence Scoring
Confidence scores are calculated based on:
- Entity type reliability
- Medical context presence
- Pattern strength
- AI detection confidence

### Medical Context Analysis
The AI service performs additional analysis for medical context:
- Medical terminology detection
- Healthcare-related content classification
- Sentiment analysis for context understanding

## Best Practices

1. Text Preparation
   - Clean and normalize text before analysis
   - Handle encoding issues
   - Consider text length (AI analysis optimal for >5 words)

2. Performance Optimization
   - Use batch processing for large datasets
   - Cache analysis results when possible
   - Monitor API usage and quotas

3. Privacy Considerations
   - Never log or store detected PHI values
   - Use secure connections for API calls
   - Implement access controls

## Error Handling

Common issues and solutions:
1. API Authentication Errors
   - Verify API key is set correctly
   - Check API permissions and quotas

2. Text Processing Errors
   - Validate input text encoding
   - Handle null or empty values
   - Check for maximum text length limits

## Integration Example

```python
# Initialize detector with both pattern and AI capabilities
detector = PHIDetector()

# Analyze medical text
medical_note = """
Patient presented to Dr. Smith on 03/15/2024 with complaints
of chest pain. Contact: (555) 123-4567
"""

# Detect PHI with combined methods
findings = detector.detect_phi(medical_note)

# Get de-identification suggestions
suggestions = detector.suggest_deidentification(
    findings,
    column_name="clinical_notes"
)

# Process results
for finding in findings:
    print(f"Found {finding['type']} with {finding['confidence']} confidence")
    print(f"Source: {finding['source']}")  # 'pattern' or 'ai'
```

## Testing and Validation

Recommended testing scenarios:
1. Mixed Content Testing
   - Combine structured and unstructured data
   - Include various PHI types
   - Test with different languages

2. Edge Cases
   - Very short text snippets
   - Long medical narratives
   - Special characters and formatting

3. Performance Testing
   - Large batch processing
   - Concurrent API calls
   - Response time monitoring

## Troubleshooting

Common issues and solutions:
1. Missing PHI Detection
   - Check if AI service is enabled
   - Verify pattern coverage
   - Review confidence thresholds

2. False Positives
   - Adjust confidence thresholds
   - Review medical context analysis
   - Update pattern definitions

3. Performance Issues
   - Monitor API latency
   - Optimize batch sizes
   - Consider caching strategies
