from typing import Dict, Any, List
import logging
from agents.base_agent import BaseAgent
from agents.symptom_agent import SymptomAgent
from agents.disease_prediction_agent import DiseasePredictionAgent
from agents.medical_knowledge_agent import MedicalKnowledgeAgent
from agents.explainable_ai_agent import ExplainableAIAgent
from agents.recommendation_agent import RecommendationAgent
from agents.report_summary_agent import ReportSummaryAgent

logger = logging.getLogger(__name__)

class CoordinatorAgent(BaseAgent):
    """Orchestrates all AI agents and merges responses"""
    
    def __init__(self):
        super().__init__(
            name="Coordinator Agent",
            description="Orchestrates all AI agents and merges their responses"
        )
        
        self.agents = {
            'symptom': SymptomAgent(),
            'prediction': DiseasePredictionAgent(),
            'knowledge': MedicalKnowledgeAgent(),
            'explainable': ExplainableAIAgent(),
            'recommendation': RecommendationAgent(),
            'report': ReportSummaryAgent()
        }
        
        self.logger.info(f"Coordinator initialized with {len(self.agents)} agents")
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input through all relevant agents"""
        text = input_data.get('text', '')
        report_text = input_data.get('report_text', '')
        symptoms = input_data.get('symptoms', [])
        
        agent_results = {}
        
        # 1. Symptom Analysis Agent
        if text or symptoms:
            symptom_result = self.agents['symptom'].execute({
                'text': text,
                'symptoms': symptoms
            })
            agent_results['symptom'] = symptom_result
            
            # Extract symptoms from symptom agent
            if symptom_result.get('status') == 'success':
                symptoms = symptom_result.get('symptoms', symptoms)
        
        # 2. Disease Prediction Agent
        if symptoms:
            pred_result = self.agents['prediction'].execute({
                'symptoms': symptoms
            })
            agent_results['prediction'] = pred_result
            
            # Extract disease for other agents
            disease = None
            if pred_result.get('status') == 'success' and pred_result.get('predictions'):
                disease = pred_result['predictions'][0].get('disease')
        
        # 3. Medical Knowledge Agent
        if text or disease:
            knowledge_result = self.agents['knowledge'].execute({
                'query': text,
                'symptoms': symptoms
            })
            agent_results['knowledge'] = knowledge_result
        
        # 4. Explainable AI Agent
        if symptoms:
            explain_result = self.agents['explainable'].execute({
                'symptoms': symptoms,
                'prediction': agent_results.get('prediction', {})
            })
            agent_results['explainable'] = explain_result
        
        # 5. Recommendation Agent
        rec_result = self.agents['recommendation'].execute({
            'symptoms': symptoms,
            'disease': disease or ''
        })
        agent_results['recommendation'] = rec_result
        
        # 6. Report Summary Agent (if report text provided)
        if report_text:
            report_result = self.agents['report'].execute({
                'text': report_text
            })
            agent_results['report'] = report_result
        
        # Merge all responses
        merged_response = self._merge_responses(agent_results)
        
        return {
            'response': merged_response,
            'agent_results': agent_results
        }
    
    def _merge_responses(self, agent_results: Dict[str, Any]) -> str:
        """Merge responses from all agents"""
        parts = []
        
        # Symptom Analysis
        if 'symptom' in agent_results and agent_results['symptom'].get('status') == 'success':
            parts.append(agent_results['symptom'].get('response', ''))
        
        # Disease Prediction
        if 'prediction' in agent_results and agent_results['prediction'].get('status') == 'success':
            parts.append(agent_results['prediction'].get('response', ''))
        
        # Medical Knowledge
        if 'knowledge' in agent_results and agent_results['knowledge'].get('status') == 'success':
            parts.append(agent_results['knowledge'].get('response', ''))
        
        # Explainable AI
        if 'explainable' in agent_results and agent_results['explainable'].get('status') == 'success':
            parts.append(agent_results['explainable'].get('response', ''))
        
        # Recommendations
        if 'recommendation' in agent_results and agent_results['recommendation'].get('status') == 'success':
            parts.append(agent_results['recommendation'].get('response', ''))
        
        # Report Summary
        if 'report' in agent_results and agent_results['report'].get('status') == 'success':
            parts.append(agent_results['report'].get('response', ''))
        
        if not parts:
            return "I couldn't process your request. Please try again with more details."
        
        return "\n\n---\n\n".join(parts)