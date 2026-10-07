import re
from typing import Dict, Any, List
from agents.base_agent import BaseAgent

class SymptomAgent(BaseAgent):
    """Agent 1: Symptom Analysis Agent"""
    
    def __init__(self):
        super().__init__(
            name="Symptom Analysis Agent",
            description="Analyzes and categorizes user symptoms"
        )
        
        self.symptom_categories = {
            'respiratory': ['cough', 'breath', 'wheezing', 'chest'],
            'fever': ['fever', 'chills', 'sweating'],
            'digestive': ['nausea', 'vomiting', 'diarrhea', 'stomach'],
            'neurological': ['headache', 'dizziness', 'confusion'],
            'musculoskeletal': ['muscle', 'joint', 'back', 'pain'],
            'skin': ['rash', 'itching', 'redness', 'swelling'],
            'general': ['fatigue', 'weakness', 'fever', 'weight']
        }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze symptoms from user input"""
        text = input_data.get('text', '')
        symptoms = self._extract_symptoms(text)
        categorized = self._categorize_symptoms(symptoms)
        severity = self._calculate_severity(categorized)
        urgency = self._determine_urgency(severity)
        
        response = self._generate_response(symptoms, categorized, urgency)
        
        return {
            'symptoms': symptoms,
            'categories': categorized,
            'severity': severity,
            'urgency_level': urgency,
            'response': response
        }
    
    def _extract_symptoms(self, text: str) -> List[str]:
        """Extract symptoms from text"""
        symptoms = []
        text_lower = text.lower()
        
        all_symptoms = []
        for cat_symptoms in self.symptom_categories.values():
            all_symptoms.extend(cat_symptoms)
        
        for symptom in all_symptoms:
            if symptom in text_lower and symptom not in symptoms:
                symptoms.append(symptom)
        
        patterns = [
            r'(?:i have|i\'m experiencing|suffering from)\s+([a-zA-Z\s]+)',
            r'([a-zA-Z\s]+)\s+(?:pain|ache|discomfort)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                s = match.strip()
                if s and len(s) > 2 and s not in symptoms:
                    symptoms.append(s)
        
        return symptoms[:10]
    
    def _categorize_symptoms(self, symptoms: List[str]) -> Dict[str, List[str]]:
        """Categorize symptoms by body system"""
        categorized = {cat: [] for cat in self.symptom_categories}
        
        for symptom in symptoms:
            found = False
            for category, keywords in self.symptom_categories.items():
                if any(k in symptom.lower() for k in keywords):
                    categorized[category].append(symptom)
                    found = True
                    break
            if not found:
                categorized['general'].append(symptom)
        
        return categorized
    
    def _calculate_severity(self, categorized: Dict[str, List[str]]) -> int:
        """Calculate severity score (0-100)"""
        total = sum(len(s) for s in categorized.values())
        severity = total * 10
        severity += len(categorized['respiratory']) * 15
        severity += len(categorized['neurological']) * 20
        severity += len(categorized['fever']) * 10
        return min(100, severity)
    
    def _determine_urgency(self, severity: int) -> str:
        """Determine urgency level"""
        if severity >= 80: return 'emergency'
        if severity >= 50: return 'high'
        if severity >= 30: return 'medium'
        return 'low'
    
    def _generate_response(self, symptoms: List[str], categories: Dict[str, List[str]], urgency: str) -> str:
        """Generate response"""
        if not symptoms:
            return "I couldn't identify specific symptoms. Could you describe how you're feeling?"
        
        response = f"**Identified Symptoms:** {', '.join(symptoms)}\n\n"
        active = [c for c, s in categories.items() if s]
        if active:
            response += f"**Affected Systems:** {', '.join(active)}\n\n"
        
        urgency_map = {
            'emergency': "🚨 **EMERGENCY**: Seek immediate medical attention!",
            'high': "🔴 **URGENT**: These symptoms need prompt medical attention.",
            'medium': "🟡 **MODERATE**: Schedule an appointment with a doctor.",
            'low': "🟢 **MILD**: Monitor symptoms and consult if they persist."
        }
        response += urgency_map.get(urgency, urgency_map['low'])
        
        return response