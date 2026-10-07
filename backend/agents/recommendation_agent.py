from typing import Dict, Any, List
from agents.base_agent import BaseAgent

class RecommendationAgent(BaseAgent):
    """Agent 5: Recommendation Agent"""
    
    def __init__(self):
        super().__init__(
            name="Recommendation Agent",
            description="Generates personalized health recommendations"
        )
        
        self.recommendations = {
            'general': {
                'diet': [
                    'Eat a balanced diet rich in fruits and vegetables',
                    'Stay hydrated - drink at least 8 glasses of water daily',
                    'Include lean proteins and whole grains in your meals',
                    'Limit processed foods and added sugars'
                ],
                'exercise': [
                    'Aim for 30 minutes of moderate exercise daily',
                    'Include both cardio and strength training',
                    'Warm up before and cool down after exercise',
                    'Listen to your body and rest when needed'
                ],
                'lifestyle': [
                    'Get 7-8 hours of quality sleep each night',
                    'Manage stress through meditation or deep breathing',
                    'Practice good hygiene - wash hands regularly',
                    'Stay socially connected for mental well-being'
                ]
            },
            'Influenza': {
                'diet': [
                    'Stay hydrated with water, clear broths, and herbal teas',
                    'Eat vitamin C-rich foods like oranges and bell peppers',
                    'Consume protein-rich foods for immune support'
                ],
                'rest': [
                    'Get plenty of rest to help your body fight the infection',
                    'Stay home to prevent spreading the virus',
                    'Monitor temperature and fever'
                ]
            },
            'Fever': {
                'diet': [
                    'Stay hydrated - drink water, clear soups, and electrolyte drinks',
                    'Eat light, easily digestible foods like toast and bananas'
                ],
                'rest': [
                    'Rest and avoid strenuous activities',
                    'Monitor temperature regularly',
                    'Consult a doctor if fever exceeds 103°F'
                ]
            },
            'Cough': {
                'diet': [
                    'Drink warm liquids like honey-lemon tea and soups',
                    'Avoid dairy as it may thicken mucus'
                ],
                'rest': [
                    'Use a humidifier to add moisture to the air',
                    'Rest your voice and avoid irritants'
                ]
            }
        }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendations"""
        symptoms = input_data.get('symptoms', [])
        disease = input_data.get('disease', '')
        
        response = self._generate_recommendations(symptoms, disease)
        
        return {
            'response': response,
            'recommendations': response
        }
    
    def _generate_recommendations(self, symptoms: List[str], disease: str) -> str:
        """Generate personalized recommendations"""
        response = "**💡 Health Recommendations:**\n\n"
        
        # Get disease-specific recommendations
        disease_recs = self.recommendations.get(disease, {})
        
        # General recommendations
        general = self.recommendations['general']
        
        # Diet recommendations
        if disease_recs.get('diet'):
            response += "**🍎 Diet:**\n"
            for rec in disease_recs['diet']:
                response += f"  • {rec}\n"
            response += "\n"
        elif general.get('diet'):
            response += "**🍎 Diet:**\n"
            for rec in general['diet']:
                response += f"  • {rec}\n"
            response += "\n"
        
        # Exercise recommendations
        if general.get('exercise'):
            response += "**🏃 Exercise:**\n"
            for rec in general['exercise']:
                response += f"  • {rec}\n"
            response += "\n"
        
        # Rest recommendations
        if disease_recs.get('rest'):
            response += "**🛌 Rest:**\n"
            for rec in disease_recs['rest']:
                response += f"  • {rec}\n"
            response += "\n"
        
        # Lifestyle recommendations
        if general.get('lifestyle'):
            response += "**🧘 Lifestyle:**\n"
            for rec in general['lifestyle']:
                response += f"  • {rec}\n"
            response += "\n"
        
        # Emergency warning
        if any(s in ' '.join(symptoms).lower() for s in ['chest pain', 'shortness of breath', 'severe']):
            response += "**🚨 Emergency Warning:**\n"
            response += "  • Seek immediate medical attention if you experience chest pain, difficulty breathing, or severe symptoms.\n\n"
        
        response += "⚠️ These are general recommendations. Always consult your doctor for personalized advice."
        
        return response