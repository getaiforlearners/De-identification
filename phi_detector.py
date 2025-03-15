import re
import logging
from typing import List, Dict, Any, Tuple
import json
from ai_service import AIPhiDetector

logger = logging.getLogger(__name__)

class PHIDetector:
    """
    A class to detect Protected Health Information (PHI) in text data.
    Similar to Presidio but focused on healthcare data.
    """

    def __init__(self):
        # Initialize patterns for different types of PHI
        self.patterns = {
            'patient_id': [
                r'(?i)(?:patient|pt|pat)[\s#.-]*(\d{4,10})',
                r'(?i)(?:mrn|medical record number|patient identifier)[\s#.-]*(\d{4,10})'
            ],
            'ssn': [
                r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b',
                r'(?i)(?:ssn|social security|social security number)[\s#:.-]*\d{3}[-.]?\d{2}[-.]?\d{4}'
            ],
            'phone': [
                r'\b(?:\+?1[-.]?)?\s*\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                r'(?i)(?:phone|tel|telephone|mobile|cell)[\s#:.-]*(?:\+?1[-.]?)?\s*\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
            ],
            'email': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                r'(?i)(?:email|e-mail)[\s#:.-]*[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}'
            ],
            'date': [
                r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',
                r'(?i)(?:dob|date of birth|birth date)[\s#:.-]*(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})'
            ],
            'age': [
                r'\b(?:age[ds]?\s*(?::|is|at|=|\s)\s*(\d{1,3})|\b\d{1,3}\s*(?:years?\s*old|y/?o))\b',
                r'(?i)(?:years of age|year old|years old)[\s#:.-]*(\d{1,3})'
            ],
            'provider_id': [
                r'\b(?:NPI|National Provider Identifier)[\s#:.-]*\d{10}\b',
                r'\b(?:DEA|Drug Enforcement Administration)[\s#:.-]*[A-Z]\d{8}\b',
                r'\b(?:State License)[\s#:.-]*[A-Z]\d{6,7}\b'
            ],
            'medical_record': [
                r'\b(?:MRN|Medical Record Number|Chart Number)[\s#:.-]*\d{4,10}\b',
                r'\b(?:Visit Number|Encounter ID)[\s#:.-]*\d{4,12}\b'
            ],
            'insurance': [
                r'\b(?:Insurance ID|Policy Number|Member ID)[\s#:.-]*[A-Z0-9]{6,20}\b',
                r'\b(?:Group Number|Plan ID)[\s#:.-]*[A-Z0-9]{4,15}\b'
            ],
            'device_id': [
                r'\b(?:Device ID|Serial Number|Model Number)[\s#:.-]*[A-Z0-9-]{4,20}\b',
                r'\b(?:UDI|Unique Device Identifier)[\s#:.-]*[A-Z0-9-]{4,20}\b'
            ],
            'facility_id': [
                r'\b(?:Facility ID|Hospital Number)[\s#:.-]*[A-Z0-9-]{4,15}\b',
                r'\b(?:Department ID|Unit Number)[\s#:.-]*[A-Z0-9-]{3,10}\b'
            ],
            'zipcode': [
                r'\b\d{5}(?:[-\s]\d{4})?\b',
                r'(?i)(?:zip|zipcode|postal code)[\s#:.-]*\d{5}(?:[-\s]\d{4})?'
            ],
            'address': [
                r'\b\d{1,5}\s+([A-Z][a-z]+\s*)+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)\b',
                r'(?i)(?:address|location|residence)[\s#:.-]*\d{1,5}\s+([A-Z][a-z]+\s*)+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)'
            ]
        }

        # Named entity patterns for identifying names
        self.name_patterns = {
            'prefix': r'\b(?:Dr|Mr|Mrs|Ms|Miss|Prof)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b',
            'name': r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b',
            'medical_title': r'\b(?:MD|DO|RN|LPN|PA|NP|CRNA|PT|OT)(?:\s|$)',
            'credential': r'\b[A-Z]{2,4}(?:-[A-Z]{1,3})?(?:\s|$)'
        }

        # Compile all patterns
        self.compiled_patterns = {}
        for category, pattern_list in self.patterns.items():
            self.compiled_patterns[category] = [re.compile(pattern) for pattern in pattern_list]
        for name, pattern in self.name_patterns.items():
            self.compiled_patterns[name] = [re.compile(pattern)]

        try:
            self.ai_detector = AIPhiDetector()
            self.ai_enabled = True
        except Exception as e:
            logger.warning(f"AI detection disabled: {str(e)}")
            self.ai_enabled = False

    def detect_phi(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PHI in the given text using both pattern matching and AI detection.
        """
        if not text or not isinstance(text, str):
            return []

        # Get pattern-based findings
        findings = []
        for phi_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.finditer(text)
                for match in matches:
                    context = self._get_context(text, match.start(), match.end())
                    findings.append({
                        'type': phi_type,
                        'value': match.group(0),
                        'start': match.start(),
                        'end': match.end(),
                        'context': context,
                        'confidence': self._calculate_confidence(phi_type, match.group(0), context),
                        'source': 'pattern'
                    })

        # Add AI-based findings if available
        if self.ai_enabled and len(text.split()) > 5:  # Only use AI for longer text
            try:
                ai_findings = self.ai_detector.analyze_medical_text(text)
                for finding in ai_findings['findings']:
                    # Avoid duplicates
                    if not any(self._is_overlapping(finding, f) for f in findings):
                        finding['source'] = 'ai'
                        findings.append(finding)
            except Exception as e:
                logger.error(f"Error in AI PHI detection: {str(e)}")

        return sorted(findings, key=lambda x: x['start'])

    def _get_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """Get surrounding context for a match."""
        text_start = max(0, start - window)
        text_end = min(len(text), end + window)
        return text[text_start:text_end]

    def _calculate_confidence(self, phi_type: str, value: str, context: str = "") -> float:
        """
        Calculate confidence score for a PHI detection.
        Returns a score between 0 and 1.
        """
        # Base confidence scores for different types
        base_scores = {
            'ssn': 0.95,
            'phone': 0.90,
            'email': 0.95,
            'date': 0.85,
            'patient_id': 0.90,
            'provider_id': 0.92,
            'medical_record': 0.93,
            'insurance': 0.88,
            'device_id': 0.85,
            'facility_id': 0.87,
            'zipcode': 0.80,
            'address': 0.85,
            'age': 0.75,
            'name': 0.70,
            'prefix': 0.80,
            'medical_title': 0.85,
            'credential': 0.82
        }

        # Get base score
        score = base_scores.get(phi_type, 0.5)

        # Adjust based on context and pattern characteristics
        if context:
            # Check for medical context indicators
            medical_terms = ['patient', 'doctor', 'hospital', 'clinic', 'medical', 'health']
            if any(term in context.lower() for term in medical_terms):
                score += 0.05

        # Adjust based on value characteristics
        if phi_type in ['name', 'prefix']:
            score += 0.1 if len(value.split()) > 1 else 0
        elif phi_type == 'address':
            score += 0.1 if len(value.split()) > 3 else 0

        return min(0.99, score)  # Cap at 0.99

    def suggest_deidentification(self, findings: List[Dict[str, Any]], column_name: str = None) -> List[Dict[str, Any]]:
        """
        Suggest de-identification methods for detected PHI.
        Takes into account column name for context-aware suggestions.
        """
        suggestions = []

        for finding in findings:
            suggestion = {
                'original': finding['value'],
                'type': finding['type'],
                'confidence': finding['confidence'],
                'methods': []
            }

            # Base methods by PHI type
            if finding['type'] in ['ssn', 'patient_id', 'medical_record', 'provider_id', 'insurance']:
                suggestion['methods'].extend([
                    {
                        'method': 'hash',
                        'description': 'One-way hash the identifier',
                        'reversible': False,
                        'priority': 1
                    },
                    {
                        'method': 'random_id',
                        'description': 'Replace with random identifier',
                        'reversible': True,
                        'priority': 2
                    }
                ])

            elif finding['type'] in ['phone', 'email']:
                suggestion['methods'].extend([
                    {
                        'method': 'mask',
                        'description': 'Mask with ***',
                        'reversible': False,
                        'priority': 1
                    },
                    {
                        'method': 'k_anonymize',
                        'description': 'Replace with generalized form',
                        'reversible': False,
                        'priority': 2
                    }
                ])

            elif finding['type'] == 'date':
                suggestion['methods'].extend([
                    {
                        'method': 'shift',
                        'description': 'Shift dates by random number of days',
                        'reversible': True,
                        'priority': 1
                    },
                    {
                        'method': 'generalize',
                        'description': 'Keep only month and year',
                        'reversible': False,
                        'priority': 2
                    }
                ])

            elif finding['type'] == 'zipcode':
                suggestion['methods'].extend([
                    {
                        'method': 'truncate',
                        'description': 'Keep only first 3 digits',
                        'reversible': False,
                        'priority': 1
                    },
                    {
                        'method': 'randomize',
                        'description': 'Replace with random valid zipcode',
                        'reversible': False,
                        'priority': 2
                    }
                ])

            elif finding['type'] in ['name', 'prefix', 'address']:
                suggestion['methods'].extend([
                    {
                        'method': 'pseudonym',
                        'description': 'Replace with pseudonym',
                        'reversible': True,
                        'priority': 1
                    },
                    {
                        'method': 'redact',
                        'description': 'Completely redact the value',
                        'reversible': False,
                        'priority': 2
                    }
                ])

            # Add column-specific suggestions
            if column_name:
                column_lower = column_name.lower()
                if 'note' in column_lower or 'comment' in column_lower:
                    suggestion['methods'].append({
                        'method': 'smart_redact',
                        'description': 'Selectively redact only PHI while preserving context',
                        'reversible': False,
                        'priority': 1
                    })
                elif 'id' in column_lower or 'identifier' in column_lower:
                    suggestion['methods'].append({
                        'method': 'consistent_hash',
                        'description': 'Use consistent hashing across related tables',
                        'reversible': True,
                        'priority': 1
                    })

            suggestions.append(suggestion)

        return suggestions

    def analyze_database_column(self, column_name: str, sample_data: List[str]) -> Dict[str, Any]:
        """
        Analyze a database column for PHI content.
        Returns statistics about detected PHI with column-specific context.
        """
        total_rows = len(sample_data)
        phi_stats = {}

        for text in sample_data:
            if not text or not isinstance(text, str):
                continue

            findings = self.detect_phi(text)
            for finding in findings:
                phi_type = finding['type']
                if phi_type not in phi_stats:
                    phi_stats[phi_type] = {
                        'count': 0,
                        'confidence_sum': 0,
                        'examples': [],
                        'contexts': set()
                    }

                phi_stats[phi_type]['count'] += 1
                phi_stats[phi_type]['confidence_sum'] += finding['confidence']
                if len(phi_stats[phi_type]['examples']) < 3:  # Keep up to 3 examples
                    phi_stats[phi_type]['examples'].append(finding['value'])
                if finding.get('context'):
                    phi_stats[phi_type]['contexts'].add(finding['context'])

        # Calculate statistics and format results
        results = {
            'column_name': column_name,
            'total_rows': total_rows,
            'phi_detected': len(phi_stats) > 0,
            'phi_types': []
        }

        for phi_type, stats in phi_stats.items():
            results['phi_types'].append({
                'type': phi_type,
                'frequency': stats['count'] / total_rows,
                'avg_confidence': stats['confidence_sum'] / stats['count'] if stats['count'] > 0 else 0,
                'example_values': stats['examples'],
                'contexts': list(stats['contexts'])[:3]  # Limit to 3 contexts
            })

        # Add column-specific analysis
        results['column_analysis'] = self._analyze_column_characteristics(column_name)

        return results

    def _analyze_column_characteristics(self, column_name: str) -> Dict[str, Any]:
        """Analyze column name for potential PHI characteristics."""
        column_lower = column_name.lower()
        characteristics = {
            'likely_phi': False,
            'phi_categories': [],
            'sensitivity_level': 'low'
        }

        # Check for common PHI indicators in column name
        phi_indicators = {
            'high': ['ssn', 'social', 'dob', 'birth', 'license', 'patient', 'mrn', 'medical'],
            'medium': ['name', 'address', 'phone', 'email', 'zip', 'postal', 'provider', 'doctor'],
            'low': ['id', 'number', 'date', 'code', 'location']
        }

        for level, indicators in phi_indicators.items():
            if any(indicator in column_lower for indicator in indicators):
                characteristics['likely_phi'] = True
                characteristics['sensitivity_level'] = level
                characteristics['phi_categories'].extend([
                    indicator for indicator in indicators
                    if indicator in column_lower
                ])

        return characteristics
    
    def _is_overlapping(self, finding1: Dict[str, Any], finding2: Dict[str, Any]) -> bool:
        """Check if two findings overlap in the text."""
        return not (finding1['end'] <= finding2['start'] or finding2['end'] <= finding1['start'])