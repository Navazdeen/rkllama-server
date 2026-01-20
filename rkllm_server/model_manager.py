"""
Model Manager for RKLLM Servers

Handles:
- Model discovery and indexing from a model folder
- Model loading and switching
- Model metadata management (from modelfile)
- Model pulling from HuggingFace repositories
- Resource cleanup and memory management
"""

import os
import json
import subprocess
import threading
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import requests
from urllib.parse import urlparse


@dataclass
class ModelMetadata:
    """Model metadata from modelfile"""
    name: str
    platform: str = "rk3588"
    system_prompt: str = "You are a helpful assistant."
    max_context_length: int = 4096
    max_new_tokens: int = 4096
    temperature: float = 0.8
    top_k: int = 1
    top_p: float = 0.9
    description: str = ""
    model_type: str = "rkllm"
    created_at: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelMetadata':
        """Create from dictionary"""
        return cls(**data)


class ModelFile:
    """Handle modelfile format for RKLLM models"""
    
    MODELFILE_NAME = "modelfile"
    
    @staticmethod
    def parse_modelfile(model_path: str) -> Optional[ModelMetadata]:
        """Parse modelfile and return metadata"""
        modelfile_path = os.path.join(model_path, ModelFile.MODELFILE_NAME)
        
        if not os.path.exists(modelfile_path):
            return None
        
        try:
            with open(modelfile_path, 'r') as f:
                data = json.load(f)
            return ModelMetadata.from_dict(data)
        except Exception as e:
            print(f"❌ Error parsing modelfile: {e}")
            return None
    
    @staticmethod
    def create_modelfile(model_path: str, metadata: ModelMetadata) -> bool:
        """Create modelfile in model directory"""
        try:
            modelfile_path = os.path.join(model_path, ModelFile.MODELFILE_NAME)
            
            # Ensure directory exists
            os.makedirs(model_path, exist_ok=True)
            
            # Add creation timestamp
            metadata.created_at = datetime.now().isoformat()
            
            with open(modelfile_path, 'w') as f:
                json.dump(metadata.to_dict(), f, indent=2)
            
            print(f"✅ Created modelfile: {modelfile_path}")
            return True
        except Exception as e:
            print(f"❌ Error creating modelfile: {e}")
            return False
    
    @staticmethod
    def parse_from_string(content: str) -> Optional[ModelMetadata]:
        """Parse modelfile from string format"""
        try:
            data = json.loads(content)
            return ModelMetadata.from_dict(data)
        except Exception as e:
            print(f"❌ Error parsing modelfile string: {e}")
            return None


class ModelManager:
    """Manages model discovery, loading, and switching"""
    
    def __init__(self, model_folder: str, platform: str = "rk3588"):
        """
        Initialize Model Manager
        
        Args:
            model_folder: Path to folder containing models
            platform: Target platform (rk3588, rk3576, rk3562, rv1126b)
        """
        self.model_folder = Path(model_folder)
        self.platform = platform
        self.lock = threading.Lock()
        self.current_model_name: Optional[str] = None
        self.models_cache: Dict[str, Dict[str, Any]] = {}
        self.model_metadata: Dict[str, ModelMetadata] = {}
        
        # Ensure model folder exists
        self.model_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Model Manager initialized with folder: {self.model_folder}")
        print(f"🎯 Target platform: {self.platform}")
    
    def discover_models(self) -> Dict[str, str]:
        """
        Discover all available models in model folder
        
        Returns:
            Dict mapping model name to model path
        """
        models = {}
        
        if not self.model_folder.exists():
            print(f"⚠️  Model folder does not exist: {self.model_folder}")
            return models
        
        # Look for model folders containing .rkllm files
        for item in self.model_folder.iterdir():
            if not item.is_dir():
                continue
            
            model_name = item.name
            
            # Check for .rkllm model files
            rkllm_files = list(item.glob("*.rkllm"))
            
            if rkllm_files:
                model_path = str(rkllm_files[0])  # Use first .rkllm file found
                models[model_name] = model_path
                
                # Load metadata if available
                metadata = ModelFile.parse_modelfile(str(item))
                if metadata:
                    self.model_metadata[model_name] = metadata
                
                self.models_cache[model_name] = {
                    "path": model_path,
                    "name": model_name,
                    "discovered_at": datetime.now().isoformat()
                }
        
        print(f"✅ Discovered {len(models)} models: {list(models.keys())}")
        return models
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get all available models with metadata"""
        self.discover_models()
        return self.models_cache
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model"""
        if model_name not in self.models_cache:
            self.discover_models()
        
        if model_name not in self.models_cache:
            return None
        
        info = self.models_cache[model_name].copy()
        
        # Add metadata if available
        if model_name in self.model_metadata:
            info["metadata"] = self.model_metadata[model_name].to_dict()
        
        return info
    
    def get_model_path(self, model_name: str) -> Optional[str]:
        """Get path to specific model"""
        if model_name not in self.models_cache:
            self.discover_models()
        
        if model_name in self.models_cache:
            return self.models_cache[model_name]["path"]
        
        return None
    
    def get_model_metadata(self, model_name: str) -> Optional[ModelMetadata]:
        """Get metadata for a model"""
        if model_name not in self.model_metadata:
            # Try to load from modelfile
            model_path = self.get_model_path(model_name)
            if model_path:
                model_dir = os.path.dirname(model_path)
                metadata = ModelFile.parse_modelfile(model_dir)
                if metadata:
                    self.model_metadata[model_name] = metadata
        
        return self.model_metadata.get(model_name)
    
    def set_current_model(self, model_name: str) -> bool:
        """Set current model"""
        if model_name not in self.models_cache:
            self.discover_models()
        
        if model_name not in self.models_cache:
            print(f"❌ Model not found: {model_name}")
            return False
        
        self.current_model_name = model_name
        print(f"✅ Current model set to: {model_name}")
        return True
    
    def get_current_model(self) -> Optional[str]:
        """Get current model name"""
        return self.current_model_name
    
    def get_current_model_path(self) -> Optional[str]:
        """Get current model path"""
        if not self.current_model_name:
            return None
        return self.get_model_path(self.current_model_name)


class ModelPuller:
    """Pull models from HuggingFace and organize them"""
    
    def __init__(self, model_folder: str):
        """
        Initialize Model Puller
        
        Args:
            model_folder: Destination folder for models
        """
        self.model_folder = Path(model_folder)
        self.model_folder.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def parse_hf_url(url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse HuggingFace URL to extract owner and repo
        
        Args:
            url: URL like https://huggingface.co/owner/repo or owner/repo
        
        Returns:
            Tuple of (owner, repo) or (None, None) if invalid
        """
        # Handle full URL
        if url.startswith("http"):
            parsed = urlparse(url)
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
        # Handle short format owner/repo
        elif "/" in url:
            parts = url.split("/")
            if len(parts) == 2:
                return parts[0], parts[1]
        
        return None, None
    
    def pull_model(self, hf_repo_url: str, model_name: Optional[str] = None,
                   system_prompt: str = "You are a helpful assistant.",
                   metadata: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Pull model from HuggingFace repository
        
        Args:
            hf_repo_url: HuggingFace repository URL (https://huggingface.co/owner/repo or owner/repo)
            model_name: Custom name for the model (uses repo name if not provided)
            system_prompt: System prompt for the model
            metadata: Additional metadata dictionary
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Parse HF URL
            owner, repo = self.parse_hf_url(hf_repo_url)
            if not owner or not repo:
                return False, f"❌ Invalid HuggingFace URL: {hf_repo_url}"
            
            # Use repo name as model name if not specified
            if not model_name:
                model_name = repo
            
            # Create model folder
            model_dir = self.model_folder / model_name
            model_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"📥 Pulling model: {owner}/{repo}")
            print(f"📁 Destination: {model_dir}")
            
            # Use HuggingFace CLI to download
            # Assuming huggingface_hub is installed
            try:
                from huggingface_hub import hf_hub_download
                
                # Download all .rkllm files from the repo
                # First, we need to list files in the repo
                from huggingface_hub import list_repo_files
                
                print(f"🔍 Scanning repository for .rkllm files...")
                
                # Try using git lfs or huggingface_hub
                # For now, use huggingface-cli command
                result = subprocess.run([
                    "huggingface-cli", "download",
                    f"{owner}/{repo}",
                    "--repo-type", "model",
                    "--local-dir", str(model_dir),
                    "--local-dir-use-symlinks", "False"
                ], capture_output=True, text=True, timeout=3600)
                
                if result.returncode != 0:
                    return False, f"❌ Failed to pull model: {result.stderr}"
                
                print(f"✅ Model pulled successfully")
                
            except ImportError:
                # Fallback to git clone if huggingface_hub not available
                print(f"⚠️  huggingface_hub not available, trying git clone...")
                
                hf_url = f"https://huggingface.co/{owner}/{repo}.git"
                result = subprocess.run([
                    "git", "clone", "--depth", "1", hf_url, str(model_dir)
                ], capture_output=True, text=True, timeout=3600)
                
                if result.returncode != 0:
                    return False, f"❌ Failed to clone repository: {result.stderr}"
                
                print(f"✅ Model repository cloned successfully")
            
            # Create modelfile with metadata
            model_metadata = ModelMetadata(
                name=model_name,
                system_prompt=system_prompt,
                description=f"Model from: {owner}/{repo}"
            )
            
            # Add any additional metadata
            if metadata:
                for key, value in metadata.items():
                    if hasattr(model_metadata, key):
                        setattr(model_metadata, key, value)
            
            # Create modelfile
            if ModelFile.create_modelfile(str(model_dir), model_metadata):
                print(f"✅ Created modelfile for: {model_name}")
            
            return True, f"✅ Model pulled successfully: {model_name}"
        
        except subprocess.TimeoutExpired:
            return False, "❌ Model pull timed out (>1 hour)"
        except Exception as e:
            return False, f"❌ Error pulling model: {str(e)}"
    
    def verify_model(self, model_name: str) -> Tuple[bool, str]:
        """Verify that a model has required files"""
        model_dir = self.model_folder / model_name
        
        if not model_dir.exists():
            return False, f"❌ Model directory not found: {model_dir}"
        
        # Check for .rkllm file
        rkllm_files = list(model_dir.glob("*.rkllm"))
        if not rkllm_files:
            return False, f"❌ No .rkllm file found in: {model_dir}"
        
        # Check for modelfile
        modelfile_path = model_dir / ModelFile.MODELFILE_NAME
        if not modelfile_path.exists():
            return False, f"⚠️  No modelfile found (optional): {modelfile_path}"
        
        return True, f"✅ Model verified: {model_name}"


class ModelResourceManager:
    """Manage model resource cleanup and memory"""
    
    def __init__(self):
        """Initialize resource manager"""
        self.current_model_handle = None
        self.lock = threading.Lock()
    
    def cleanup_model(self, model_handle: Any) -> bool:
        """
        Cleanup model resources
        
        Args:
            model_handle: Model handle to cleanup
        
        Returns:
            Success status
        """
        try:
            with self.lock:
                if model_handle and hasattr(model_handle, 'release'):
                    model_handle.release()
                    print("✅ Model resources cleaned up")
                    return True
        except Exception as e:
            print(f"❌ Error cleaning up resources: {e}")
        
        return False
    
    def switch_model(self, old_model: Any, new_model: Any) -> bool:
        """
        Switch from one model to another
        
        Args:
            old_model: Current model to cleanup
            new_model: New model to switch to
        
        Returns:
            Success status
        """
        try:
            with self.lock:
                # Cleanup old model
                if old_model:
                    if hasattr(old_model, 'release'):
                        old_model.release()
                    if hasattr(old_model, 'destroy'):
                        old_model.destroy()
                
                # Set new model as current
                self.current_model_handle = new_model
                
                print("✅ Model switched successfully")
                return True
        except Exception as e:
            print(f"❌ Error switching models: {e}")
            return False
    
    def get_current_model(self) -> Any:
        """Get current model handle"""
        return self.current_model_handle


# Convenience functions
def discover_models(model_folder: str) -> Dict[str, str]:
    """Convenience function to discover models"""
    manager = ModelManager(model_folder)
    models = manager.discover_models()
    return {name: info["path"] for name, info in manager.get_available_models().items()}


def get_model_metadata(model_folder: str, model_name: str) -> Optional[ModelMetadata]:
    """Convenience function to get model metadata"""
    manager = ModelManager(model_folder)
    return manager.get_model_metadata(model_name)


def pull_model_from_hf(model_folder: str, hf_url: str, model_name: Optional[str] = None) -> Tuple[bool, str]:
    """Convenience function to pull model from HuggingFace"""
    puller = ModelPuller(model_folder)
    return puller.pull_model(hf_url, model_name)
