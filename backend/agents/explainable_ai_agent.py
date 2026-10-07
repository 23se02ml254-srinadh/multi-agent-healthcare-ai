from typing import Dict, Any, List
from agents.base_agent import BaseAgent

class ExplainableAIAgent(BaseAgent):
    """Agent 4: Explainable AI Agent"""
    
    def __init__(self):
        super().__init__(
            name="Explainable AI Agent",
            description="Explains why the AI made a prediction"
        )
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate explanation for prediction"""
        symptoms = input_data.get('symptoms', [])
        prediction = input_data.get('prediction', {})
        
        if not symptoms:
            return {
                'response': "No symptoms provided for explanation."
            }
        
        predictions_list = prediction.get('predictions', [])
        if predictions_list:
            disease = predictions_list[0].get('disease', 'Unknown')
            confidence = predictions_list[0].get('confidence', 0.0)
        else:
            disease = 'Unknown'
            confidence = 0.0
        
        # Generate feature importance (simulated)
        feature_importance = self._calculate_feature_importance(symptoms)
        
        response = self._generate_response(disease, confidence, feature_importance, symptoms)
        
        return {
            'feature_importance': feature_importance,
            'disease': disease,
            'confidence': confidence,
            'response': response
        }
    
    def _calculate_feature_importance(self, symptoms: List[str]) -> List[Dict]:
        """Calculate feature importance (simulated SHAP values)"""
        # In production, use actual SHAP/LIME
        importance = []
        weights = {
            'fever': 45,
            'cough': 35,
            'headache': 30,
            'fatigue': 25,
            'shortness_of_breath': 40,
            'chest_pain': 35,
            'nausea': 20,
            'muscle_pain': 25,
            'sore_throat': 20,
            'runny_nose': 15,
            'sneezing': 15
        }
        
        for symptom in symptoms:
            weight = weights.get(symptom.lower(), 10)
            importance.append({
                'symptom': symptom,
                'importance': weight
            })
        
        importance.sort(key=lambda x: x['importance'], reverse=True)
        return importance[:5]
    
    def _generate_response(self, disease: str, confidence: float, 
                          feature_importance: List[Dict], symptoms: List[str]) -> str:
        """Generate explanation response"""
        if not feature_importance:
            return "No explanation available for this prediction."
        
        response = f"**🔍 Why {disease} was predicted:**\n\n"
        response += f"Confidence: {confidence * 100:.1f}%\n\n"
        response += "**Most Important Symptoms:**\n"
        
        for item in feature_importance:
            response += f"  • {item['symptom']}: {item['importance']}% influence\n"
        
        response += "\n**Simple Explanation:**\n"
        response += f"The AI predicted {disease} because you reported these key symptoms: "
        response += f"{', '.join([s['symptom'] for s in feature_importance[:3]])}.\n"
        response += "These symptoms are commonly associated with this condition.\n\n"
        
        response += "⚠️ This is an AI explanation. Always consult a doctor for accurate diagnosis."
        
        return response