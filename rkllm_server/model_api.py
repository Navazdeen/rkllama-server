"""
Model Management API

Provides endpoints for:
- List available models
- Switch models
- Get model info
- Pull models from HuggingFace
"""

from typing import Dict, Any, Optional, Tuple
from model_manager import ModelManager, ModelPuller, ModelFile, ModelMetadata
import json


class ModelAPI:
    """API for model management"""
    
    def __init__(self, model_folder: str, platform: str = "rk3588"):
        """Initialize Model API"""
        self.manager = ModelManager(model_folder, platform)
        self.puller = ModelPuller(model_folder)
    
    def list_models(self) -> Dict[str, Any]:
        """List all available models"""
        models = self.manager.get_available_models()
        return {
            "success": True,
            "models": models,
            "current_model": self.manager.get_current_model(),
            "total": len(models)
        }
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get detailed information about a model"""
        info = self.manager.get_model_info(model_name)
        
        if not info:
            return {
                "success": False,
                "error": f"Model not found: {model_name}"
            }
        
        return {
            "success": True,
            "model": info
        }
    
    def switch_model(self, model_name: str) -> Dict[str, Any]:
        """Switch to a different model"""
        success = self.manager.set_current_model(model_name)
        
        if not success:
            return {
                "success": False,
                "error": f"Failed to switch to model: {model_name}"
            }
        
        return {
            "success": True,
            "message": f"Switched to model: {model_name}",
            "current_model": model_name,
            "model_path": self.manager.get_current_model_path()
        }
    
    def pull_model(self, hf_url: str, model_name: Optional[str] = None,
                   system_prompt: Optional[str] = None,
                   metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Pull model from HuggingFace"""
        
        if not system_prompt:
            system_prompt = "You are a helpful assistant."
        
        success, message = self.puller.pull_model(
            hf_url,
            model_name,
            system_prompt,
            metadata
        )
        
        if success:
            # Discover the new model
            self.manager.discover_models()
            
            # Set it as current if needed
            actual_model_name = model_name or hf_url.split("/")[-1]
            self.manager.set_current_model(actual_model_name)
        
        return {
            "success": success,
            "message": message
        }
    
    def verify_model(self, model_name: str) -> Dict[str, Any]:
        """Verify a model"""
        success, message = self.puller.verify_model(model_name)
        
        return {
            "success": success,
            "message": message
        }
    
    def get_current_model(self) -> Dict[str, Any]:
        """Get current model info"""
        current = self.manager.get_current_model()
        
        if not current:
            return {
                "success": False,
                "error": "No model currently selected"
            }
        
        return {
            "success": True,
            "current_model": current,
            "path": self.manager.get_current_model_path(),
            "metadata": self.manager.get_model_metadata(current).to_dict() if self.manager.get_model_metadata(current) else None
        }
    
    def create_modelfile(self, model_name: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update modelfile for a model"""
        model_path = self.manager.get_model_path(model_name)
        
        if not model_path:
            return {
                "success": False,
                "error": f"Model not found: {model_name}"
            }
        
        try:
            import os
            model_dir = os.path.dirname(model_path)
            
            # Create ModelMetadata from dict
            model_meta = ModelMetadata(**metadata)
            
            success = ModelFile.create_modelfile(model_dir, model_meta)
            
            if success:
                self.manager.model_metadata[model_name] = model_meta
            
            return {
                "success": success,
                "message": f"Modelfile {'created' if success else 'creation failed'} for: {model_name}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error creating modelfile: {str(e)}"
            }
    
    def get_modelfile(self, model_name: str) -> Dict[str, Any]:
        """Get modelfile content for a model"""
        model_path = self.manager.get_model_path(model_name)
        
        if not model_path:
            return {
                "success": False,
                "error": f"Model not found: {model_name}"
            }
        
        import os
        model_dir = os.path.dirname(model_path)
        metadata = ModelFile.parse_modelfile(model_dir)
        
        if not metadata:
            return {
                "success": False,
                "error": f"No modelfile found for: {model_name}"
            }
        
        return {
            "success": True,
            "modelfile": metadata.to_dict()
        }
