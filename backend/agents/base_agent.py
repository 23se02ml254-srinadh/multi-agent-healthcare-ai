from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all AI agents"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logger
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and return results"""
        pass
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent with error handling"""
        try:
            self.logger.info(f"{self.name} started processing")
            result = self.process(input_data)
            result['agent'] = self.name
            result['status'] = 'success'
            return result
        except Exception as e:
            self.logger.error(f"{self.name} error: {str(e)}")
            return {
                'agent': self.name,
                'status': 'error',
                'error': str(e),
                'response': f"Sorry, I encountered an error: {str(e)}"
            }