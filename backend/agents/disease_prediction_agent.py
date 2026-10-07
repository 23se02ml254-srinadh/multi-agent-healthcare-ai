import random
from typing import Dict, Any, List
from agents.base_agent import BaseAgent

class DiseasePredictionAgent(BaseAgent):
    """Agent 2: Disease Prediction Agent"""
    
    def __init__(self):
        super().__init__(
            name="Disease Prediction Agent",
            description="Predicts diseases from symptoms using ML models"
        )
        
        self.disease_database = {
            'Influenza': {
                'symptoms': ['fever', 'cough', 'fatigue', 'muscle_pain', 'headache'],
                'severity': 'medium',
                'urgency': 'medium',
                'specialist': 'General Physician'
            },
            'Common Cold': {
                'symptoms': ['runny_nose', 'sneezing', 'cough', 'sore_throat'],
                'severity': 'low',
                'urgency': 'low',
                'specialist': 'General Physician'
            },
            'Pneumonia': {
                'symptoms': ['fever', 'cough', 'shortness_of_breath', 'chest_pain'],
                'severity': 'high',
                'urgency': 'high',
                'specialist': 'Pulmonologist'
            },
            'Bronchitis': {
                'symptoms': ['cough', 'shortness_of_breath', 'chest_discomfort', 'fatigue'],
                'severity': 'medium',
                'urgency': 'medium',
                'specialist': 'Pulmonologist'
            },
            'Asthma': {
                'symptoms': ['shortness_of_breath', 'wheezing', 'chest_tightness', 'cough'],
                'severity': 'medium',
                'urgency': 'medium',
                'specialist': 'Pulmonologist'
            },
            'Migraine': {
                'symptoms': ['headache', 'nausea', 'sensitivity_to_light', 'dizziness'],
                'severity': 'medium',
                'urgency': 'medium',
                'specialist': 'Neurologist'
            },
            'Gastroenteritis': {
                'symptoms': ['nausea', 'vomiting', 'diarrhea', 'abdominal_pain'],
                'severity': 'medium',
                'urgency': 'medium',
                'specialist': 'Gastroenterologist'
            },
            'Allergies': {
                'symptoms': ['sneezing', 'runny_nose', 'itchy_eyes', 'skin_rash'],
                'severity': 'low',
                'urgency': 'low',
                'specialist': 'Allergist'
            },
            'Hypertension': {
                'symptoms': ['headache', 'chest_pain', 'shortness_of_breath', 'dizziness'],
                'severity': 'high',
                'urgency': 'high',
                'specialist': 'Cardiologist'
            },
            'Diabetes': {
                'symptoms': ['increased_thirst', 'frequent_urination', 'fatigue', 'blurred_vision'],
                'severity': 'medium',
                'urgency': 'medium',
                'specialist': 'Endocrinologist'
            }
        }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict disease from symptoms"""
        symptoms = input_data.get('symptoms', [])
        
        if not symptoms:
            return {
                'response': "Please provide symptoms for disease prediction.",
                'predictions': []
            }
        
        # Calculate matches
        matches = []
        for disease, info in self.disease_database.items():
            match_score = self._calculate_match(symptoms, info['symptoms'])
            if match_score > 0:
                matches.append({
                    'disease': disease,
                    'confidence': min(1.0, match_score / len(info['symptoms'])),
                    'info': info
                })
        
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        if not matches:
            return {
                'response': "I couldn't identify a specific disease. Please consult a doctor.",
                'predictions': []
            }
        
        # Format predictions first
        predictions = [
            {
                'disease': m['disease'],
                'confidence': m['confidence'],
                'severity': m['info']['severity'],
                'urgency': m['info']['urgency'],
                'specialist': m['info']['specialist']
            }
            for m in matches[:3]
        ]

        # Generate response
        response = self._generate_response(predictions, symptoms)
        
        return {
            'predictions': predictions,
            'response': response
        }
    
    def _calculate_match(self, symptoms: List[str], disease_symptoms: List[str]) -> int:
        """Calculate match score"""
        return sum(1 for s in symptoms if any(ds in s.lower() for ds in disease_symptoms))
    
    def _generate_response(self, predictions: List[Dict], symptoms: List[str]) -> str:
        """Generate prediction response"""
        if not predictions:
            return "No clear disease match found."
        
        response = "**🏥 Disease Prediction Results:**\n\n"
        
        for i, pred in enumerate(predictions, 1):
            response += f"**{i}. {pred['disease']}**\n"
            response += f"   • Confidence: {pred['confidence'] * 100:.1f}%\n"
            response += f"   • Severity: {pred['severity'].upper()}\n"
            response += f"   • Specialist: {pred['specialist']}\n\n"
        
        response += f"**Analyzed Symptoms:** {', '.join(symptoms)}\n\n"
        response += "⚠️ This is an AI prediction. Please consult a doctor for accurate diagnosis."
        
        return response