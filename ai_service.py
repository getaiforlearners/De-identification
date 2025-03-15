import os
import logging
from google.cloud import language_v1
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class AIPhiDetector:
    """
    AI-powered PHI detection service using Google Cloud Natural Language API
    for enhanced detection in unstructured text data.
    """

    def __init__(self):
        self.api_key = os.environ.get('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API key not found in environment variables")
        
        # Initialize Google Cloud client
        self.client = language_v1.LanguageServiceClient.from_api_key(self.api_key)

    def analyze_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyze text using Google Cloud NLP to detect potential PHI.
        """
        try:
            # Prepare the document
            document = language_v1.Document(
                content=text,
                type_=language_v1.Document.Type.PLAIN_TEXT,
                language="en"
            )

            # Analyze entities
            response = self.client.analyze_entities(
                document=document,
                encoding_type=language_v1.EncodingType.UTF8
            )

            findings = []
            for entity in response.entities:
                # Map Google entity types to PHI types
                phi_type = self._map_entity_to_phi(entity.type_.name)
                if phi_type:
                    findings.append({
                        'type': phi_type,
                        'value': entity.name,
                        'start': text.find(entity.name),
                        'end': text.find(entity.name) + len(entity.name),
                        'confidence': entity.salience,
                        'metadata': entity.metadata
                    })

            return findings

        except Exception as e:
            logger.error(f"Error in AI PHI detection: {str(e)}")
            return []

    def _map_entity_to_phi(self, entity_type: str) -> str:
        """
        Map Google entity types to PHI categories.
        """
        mapping = {
            'PERSON': 'name',
            'LOCATION': 'address',
            'ORGANIZATION': 'facility_id',
            'NUMBER': None,  # Need additional context to determine if it's PHI
            'DATE': 'date',
            'PHONE_NUMBER': 'phone',
            'ADDRESS': 'address',
            'PRICE': None,
            'EVENT': None,
        }
        return mapping.get(entity_type)

    def analyze_medical_text(self, text: str) -> Dict[str, Any]:
        """
        Specialized analysis for medical text with context awareness.
        """
        try:
            # Get basic entity analysis
            findings = self.analyze_text(text)
            
            # Additional medical-specific analysis
            document = language_v1.Document(
                content=text,
                type_=language_v1.Document.Type.PLAIN_TEXT
            )
            
            # Get document sentiment to understand context
            sentiment = self.client.analyze_sentiment(document=document)
            
            # Get content classification
            classification = self.client.classify_text(document=document)
            
            # Enhance findings with medical context
            medical_context = self._analyze_medical_context(
                findings, 
                sentiment.document_sentiment,
                classification.categories if classification.categories else []
            )
            
            return {
                'findings': findings,
                'medical_context': medical_context,
                'confidence': self._calculate_medical_confidence(findings, medical_context)
            }
            
        except Exception as e:
            logger.error(f"Error in medical text analysis: {str(e)}")
            return {'findings': [], 'medical_context': {}, 'confidence': 0.0}

    def _analyze_medical_context(self, findings: List[Dict], sentiment: Any, categories: List) -> Dict[str, Any]:
        """
        Analyze medical context of the findings.
        """
        context = {
            'is_medical_content': any('health' in cat.name.lower() or 'medical' in cat.name.lower() 
                                    for cat in categories),
            'potential_diagnosis': False,
            'contains_measurements': False,
            'contains_medications': False
        }
        
        # Additional medical context analysis
        medical_terms = ['diagnosis', 'treatment', 'prescription', 'dosage', 'symptoms']
        context['potential_diagnosis'] = any(term in str(finding['value']).lower() 
                                          for finding in findings 
                                          for term in medical_terms)
        
        return context

    def _calculate_medical_confidence(self, findings: List[Dict], context: Dict) -> float:
        """
        Calculate confidence score for medical PHI detection.
        """
        base_confidence = sum(finding.get('confidence', 0) for finding in findings) / len(findings) if findings else 0
        
        # Adjust confidence based on medical context
        if context['is_medical_content']:
            base_confidence *= 1.2
        if context['potential_diagnosis']:
            base_confidence *= 1.1
            
        return min(base_confidence, 0.99)  # Cap at 0.99
