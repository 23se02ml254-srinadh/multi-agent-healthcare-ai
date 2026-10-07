from typing import Dict, Any, List
from agents.base_agent import BaseAgent

class MedicalKnowledgeAgent(BaseAgent):
    """Agent 3: Medical Knowledge Retrieval Agent"""
    
    def __init__(self):
        super().__init__(
            name="Medical Knowledge Agent",
            description="Retrieves trusted medical knowledge"
        )
        
        self.knowledge_base = {
            'Influenza': {
                'description': 'Flu is a viral respiratory infection that can cause mild to severe illness.',
                'symptoms': ['Fever', 'Cough', 'Sore throat', 'Body aches', 'Fatigue'],
                'treatment': 'Rest, hydration, over-the-counter fever reducers',
                'prevention': 'Annual flu vaccine, hand washing, avoiding sick people',
                'risk_factors': 'Age, weakened immune system, chronic conditions'
            },
            'Common Cold': {
                'description': 'A viral infection of the upper respiratory tract.',
                'symptoms': ['Runny nose', 'Sneezing', 'Cough', 'Sore throat'],
                'treatment': 'Rest, hydration, saline nasal spray',
                'prevention': 'Hand washing, avoiding sick people',
                'risk_factors': 'Weakened immune system, stress'
            },
            'Pneumonia': {
                'description': 'An infection that inflames air sacs in the lungs.',
                'symptoms': ['Cough with phlegm', 'Fever', 'Shortness of breath', 'Chest pain'],
                'treatment': 'Antibiotics, rest, hydration, hospitalization if severe',
                'prevention': 'Vaccination, good hygiene',
                'risk_factors': 'Age, smoking, chronic diseases'
            },
            'Migraine': {
                'description': 'A neurological condition causing severe headaches.',
                'symptoms': ['Throbbing headache', 'Nausea', 'Light sensitivity', 'Sound sensitivity'],
                'treatment': 'Pain relievers, triptans, rest in dark room',
                'prevention': 'Avoid triggers, regular sleep, stress management',
                'risk_factors': 'Family history, hormonal changes'
            },
            'Diabetes': {
                'description': 'A chronic condition affecting how the body uses blood sugar.',
                'symptoms': ['Increased thirst', 'Frequent urination', 'Fatigue', 'Blurred vision'],
                'treatment': 'Insulin, diet management, exercise',
                'prevention': 'Healthy diet, regular exercise, maintaining healthy weight',
                'risk_factors': 'Family history, obesity, sedentary lifestyle'
            },
            'Hypertension': {
                'description': 'A condition where blood pressure is consistently too high.',
                'symptoms': ['Often no symptoms', 'Headache', 'Dizziness', 'Chest pain'],
                'treatment': 'Medication, lifestyle changes, diet modification',
                'prevention': 'Healthy diet, reducing sodium, regular exercise',
                'risk_factors': 'Age, family history, obesity, stress'
            },
            'Asthma': {
                'description': 'A condition causing airways to become inflamed and narrow.',
                'symptoms': ['Wheezing', 'Shortness of breath', 'Chest tightness', 'Cough'],
                'treatment': 'Inhalers, avoiding triggers, regular check-ups',
                'prevention': 'Avoid triggers, medication compliance',
                'risk_factors': 'Family history, allergies, smoking'
            }
        }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve medical knowledge"""
        query = input_data.get('query', '')
        symptoms = input_data.get('symptoms', [])
        
        # Find matching disease
        disease = self._find_disease(query, symptoms)
        
        if not disease:
            return {
                'response': "I couldn't find specific medical information. Please consult a doctor.",
                'knowledge': {}
            }
        
        info = self.knowledge_base.get(disease, {})
        
        response = self._generate_response(disease, info)
        
        return {
            'disease': disease,
            'knowledge': info,
            'response': response
        }
    
    def _find_disease(self, query: str, symptoms: List[str]) -> str:
        """Find matching disease"""
        query_lower = query.lower()
        
        # Check by disease name
        for disease in self.knowledge_base:
            if disease.lower() in query_lower:
                return disease
        
        # Check by symptoms
        for disease, info in self.knowledge_base.items():
            for symptom in info.get('symptoms', []):
                if symptom.lower() in query_lower:
                    return disease
        
        # Check symptoms list
        if symptoms:
            for disease, info in self.knowledge_base.items():
                match = sum(1 for s in symptoms if any(ds.lower() in s.lower() for ds in info.get('symptoms', [])))
                if match > 1:
                    return disease
        
        return None
    
    def _generate_response(self, disease: str, info: Dict) -> str:
        """Generate knowledge response"""
        if not info:
            return f"No detailed information available for {disease}."
        
        response = f"**📚 Medical Information: {disease}**\n\n"
        response += f"**Description:** {info.get('description', 'N/A')}\n\n"
        
        if info.get('symptoms'):
            response += f"**Common Symptoms:**\n"
            for symptom in info['symptoms']:
                response += f"  • {symptom}\n"
            response += "\n"
        
        if info.get('treatment'):
            response += f"**Treatment:** {info['treatment']}\n\n"
        
        if info.get('prevention'):
            response += f"**Prevention:** {info['prevention']}\n\n"
        
        if info.get('risk_factors'):
            response += f"**Risk Factors:** {info['risk_factors']}\n\n"
        
        response += "⚠️ This is general information. Always consult a healthcare professional."
        
        return response