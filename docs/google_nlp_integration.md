# Google Cloud Natural Language API Integration

## Overview
NoTraceHealth integrates Google Cloud Natural Language API to enhance PHI detection capabilities, particularly for unstructured text data like medical notes, reports, and comments.

## Setup and Configuration

### Prerequisites
1. Google Cloud Account
2. Enabled Natural Language API
3. API Key with appropriate permissions

### Environment Configuration
```bash
# Set API key in environment
export GOOGLE_API_KEY="your-api-key"
```

## Integration Architecture

### AIPhiDetector Class
The `AIPhiDetector` class in `ai_service.py` serves as the primary interface to Google Cloud NLP:

```python
class AIPhiDetector:
    def __init__(self):
        self.api_key = os.environ.get('GOOGLE_API_KEY')
        self.client = language_v1.LanguageServiceClient.from_api_key(self.api_key)

    def analyze_text(self, text: str) -> List[Dict[str, Any]]:
        """Analyze text using Google Cloud NLP."""
        ...

    def analyze_medical_text(self, text: str) -> Dict[str, Any]:
        """Specialized analysis for medical text."""
        ...
```

## Entity Type Mapping
Google Cloud entity types are mapped to PHI categories:

| Google Entity Type | PHI Category |
|-------------------|--------------|
| PERSON            | name         |
| LOCATION          | address      |
| ORGANIZATION      | facility_id  |
| DATE              | date         |
| PHONE_NUMBER      | phone        |
| ADDRESS           | address      |

## Features

### 1. Entity Detection
- Identifies named entities in text
- Maps to PHI categories
- Provides confidence scores

### 2. Medical Context Analysis
- Recognizes medical terminology
- Analyzes document sentiment
- Classifies content type

### 3. Enhanced Confidence Scoring
- Entity-based confidence
- Context-aware scoring
- Medical relevance weighting

## Usage Examples

### Basic Text Analysis
```python
from ai_service import AIPhiDetector

detector = AIPhiDetector()

# Analyze medical text
text = """
Patient was admitted to Memorial Hospital
on March 15, 2025. Dr. Johnson prescribed
medication for chronic condition.
"""

analysis = detector.analyze_medical_text(text)
```

### Integration with PHI Detection
```python
from phi_detector import PHIDetector

# Initialize detector with AI capabilities
detector = PHIDetector()  # Automatically initializes AI detection

# Analyze text with both pattern and AI detection
findings = detector.detect_phi(medical_text)

# Findings will include both pattern-based and AI-detected PHI
for finding in findings:
    print(f"Source: {finding['source']}")  # 'pattern' or 'ai'
    print(f"Type: {finding['type']}")
    print(f"Confidence: {finding['confidence']}")
```

## Performance Optimization

### Best Practices
1. Batch Processing
   - Group similar texts
   - Process in batches
   - Cache results when possible

2. Text Preprocessing
   - Clean input text
   - Remove irrelevant content
   - Normalize format

3. API Usage Optimization
   - Monitor API quotas
   - Implement rate limiting
   - Cache frequent requests

## Error Handling

### Common Issues
1. API Authentication
   ```python
   try:
       detector = AIPhiDetector()
   except ValueError as e:
       logger.error(f"API key error: {e}")
   ```

2. Rate Limiting
   ```python
   try:
       analysis = detector.analyze_medical_text(text)
   except Exception as e:
       if "quota" in str(e).lower():
           logger.error("API quota exceeded")
   ```

3. Invalid Input
   ```python
   if not text or len(text.strip()) < 5:
       return {'findings': [], 'confidence': 0}
   ```

## Monitoring and Logging

### Key Metrics
1. API Response Times
2. Detection Accuracy
3. False Positive Rates
4. Usage Patterns

### Logging Example
```python
import logging

logger = logging.getLogger(__name__)

def analyze_medical_text(self, text: str):
    try:
        start_time = time.time()
        result = self.client.analyze_entities(...)
        duration = time.time() - start_time
        
        logger.info(f"Analysis completed in {duration:.2f}s")
        logger.debug(f"Found {len(result.entities)} entities")
        
        return self._process_results(result)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise
```

## Testing

### Unit Tests
```python
def test_ai_detection():
    detector = AIPhiDetector()
    text = "Patient: John Doe"
    result = detector.analyze_text(text)
    
    assert len(result) > 0
    assert any(f['type'] == 'name' for f in result)
```

### Integration Tests
```python
def test_combined_detection():
    detector = PHIDetector()
    text = "Dr. Smith (555-123-4567)"
    findings = detector.detect_phi(text)
    
    assert any(f['source'] == 'pattern' for f in findings)
    assert any(f['source'] == 'ai' for f in findings)
```

## Troubleshooting Guide

### API Issues
1. Check API key validity
2. Verify API service status
3. Monitor quota usage

### Detection Issues
1. Verify text format
2. Check confidence thresholds
3. Review entity mapping

### Performance Issues
1. Monitor response times
2. Check batch sizes
3. Optimize API calls

## Future Improvements
1. Custom entity type training
2. Enhanced medical context analysis
3. Automated confidence tuning
4. Real-time analysis optimization
