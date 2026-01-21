"""
Model Management API

Provides endpoints for:
- List available models
- Switch models
- Get model info
- Pull models from HuggingFace
"""

from typing import Any, Dict, Optional

from model_manager import ModelFile, ModelManager, ModelPuller

from rkllm_server.utils.utils import ModelMetadata


class ModelAPI:
    """API for model management"""

    def __init__(self, model_folder: str, platform: str = "rk3588"):
        """Initialize Model API"""
        self.manager = ModelManager(model_folder, platform)
        self.puller = ModelPuller(model_folder)

    def listModels(self) -> Dict[str, Any]:
        """List all available models"""
        models = self.manager.getAvailableModels()
        return {
            "success": True,
            "models": models,
            "current_model": self.manager.getCurrentModel(),
            "total": len(models),
        }

    def getModelInfo(self, model_name: str) -> Dict[str, Any]:
        """Get detailed information about a model"""
        info = self.manager.getModelInfo(model_name)

        if not info:
            return {"success": False, "error": f"Model not found: {model_name}"}

        return {"success": True, "model": info}

    def switchModel(self, model_name: str) -> Dict[str, Any]:
        """Switch to a different model"""
        success = self.manager.setCurrentModel(model_name)

        if not success:
            return {
                "success": False,
                "error": f"Failed to switch to model: {model_name}",
            }

        return {
            "success": True,
            "message": f"Switched to model: {model_name}",
            "current_model": model_name,
            "model_path": self.manager.getCurrentModelPath(),
        }

    def pullModel(
        self,
        hf_url: str,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Pull model from HuggingFace"""

        if not system_prompt:
            system_prompt = "You are a helpful assistant."

        success, message = self.puller.pullModel(
            hf_url, model_name, system_prompt, metadata
        )

        if success:
            # Discover the new model
            self.manager.discoverModels()

            # Set it as current if needed
            actual_model_name = model_name or hf_url.split("/")[-1]
            self.manager.setCurrentModel(actual_model_name)

        return {"success": success, "message": message}

    def verifyModel(self, model_name: str) -> Dict[str, Any]:
        """Verify a model"""
        success, message = self.puller.verifyModel(model_name)

        return {"success": success, "message": message}

    def getCurrentModel(self) -> Dict[str, Any]:
        """Get current model info"""
        current = self.manager.getCurrentModel()

        if not current:
            return {"success": False, "error": "No model currently selected"}

        return {
            "success": True,
            "current_model": current,
            "path": self.manager.getCurrentModelPath(),
            "metadata": (
                self.manager.getModelMetadata(current).to_dict()
                if self.manager.getModelMetadata(current)
                else None
            ),
        }

    def createModelfile(
        self, model_name: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create or update modelfile for a model"""
        model_path = self.manager.getModelPath(model_name)

        if not model_path:
            return {"success": False, "error": f"Model not found: {model_name}"}

        try:
            import os

            model_dir = os.path.dirname(model_path)

            # Create ModelMetadata from dict
            model_meta = ModelMetadata(**metadata)

            success = ModelFile.createModelfile(model_dir, model_meta)

            if success:
                self.manager.model_metadata[model_name] = model_meta

            return {
                "success": success,
                "message": f"Modelfile {'created' if success else 'creation failed'} for: {model_name}",
            }
        except Exception as e:
            return {"success": False, "error": f"Error creating modelfile: {str(e)}"}

    def getModelfile(self, model_name: str) -> Dict[str, Any]:
        """Get modelfile content for a model"""
        model_path = self.manager.getModelPath(model_name)

        if not model_path:
            return {"success": False, "error": f"Model not found: {model_name}"}

        import os

        model_dir = os.path.dirname(model_path)
        metadata = ModelFile.parseModelfile(model_dir)

        if not metadata:
            return {"success": False, "error": f"No modelfile found for: {model_name}"}

        return {"success": True, "modelfile": metadata.to_dict()}
