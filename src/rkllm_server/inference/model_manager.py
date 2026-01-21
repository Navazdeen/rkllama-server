"""
Model Manager for RKLLM Servers

Handles:
- Model discovery and indexing from a model folder
- Model loading and switching
- Model metadata management (from modelfile)
- Model pulling from HuggingFace repositories
- Resource cleanup and memory management
"""

import json
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import urlparse

from rkllm_server.utils.utils import DownloadProgress, ModelMetadata


class ModelFile:
    """Handle modelfile format for RKLLM models"""

    MODELFILE_NAME = "modelfile"

    @staticmethod
    def parseModelfile(model_path: str) -> Optional[ModelMetadata]:
        """Parse modelfile and return metadata"""
        modelfile_path = os.path.join(model_path, ModelFile.MODELFILE_NAME)

        if not os.path.exists(modelfile_path):
            return None

        try:
            with open(modelfile_path, "r") as f:
                data = json.load(f)
            return ModelMetadata.from_dict(data)
        except Exception as e:
            print(f"❌ Error parsing modelfile: {e}")
            return None

    @staticmethod
    def createModelfile(model_path: str, metadata: ModelMetadata) -> bool:
        """Create modelfile in model directory"""
        try:
            modelfile_path = os.path.join(model_path, ModelFile.MODELFILE_NAME)

            # Ensure directory exists
            os.makedirs(model_path, exist_ok=True)

            # Add creation timestamp
            metadata.created_at = datetime.now().isoformat()

            with open(modelfile_path, "w") as f:
                json.dump(metadata.to_dict(), f, indent=2)

            print(f"✅ Created modelfile: {modelfile_path}")
            return True
        except Exception as e:
            print(f"❌ Error creating modelfile: {e}")
            return False

    @staticmethod
    def parseFromString(content: str) -> Optional[ModelMetadata]:
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

    def discoverModels(self) -> Dict[str, str]:
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
                metadata = ModelFile.parseModelfile(str(item))
                if metadata:
                    self.model_metadata[model_name] = metadata

                self.models_cache[model_name] = {
                    "path": model_path,
                    "name": model_name,
                    "discovered_at": datetime.now().isoformat(),
                }

        print(f"✅ Discovered {len(models)} models: {list(models.keys())}")
        return dict(sorted(models.items(), key=lambda x: x[0]))

    def getAvailableModels(self) -> Dict[str, Dict[str, Any]]:
        """Get all available models with metadata"""
        self.discoverModels()
        return self.models_cache

    def getModelInfo(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model"""
        if model_name not in self.models_cache:
            self.discoverModels()

        if model_name not in self.models_cache:
            return None

        info = self.models_cache[model_name].copy()

        # Add metadata if available
        if model_name in self.model_metadata:
            info["metadata"] = self.model_metadata[model_name].to_dict()

        return info

    def getModelPath(self, model_name: str) -> Optional[str]:
        """Get path to specific model"""
        if model_name not in self.models_cache:
            self.discoverModels()

        if model_name in self.models_cache:
            return self.models_cache[model_name]["path"]

        return None

    def getModelMetadata(self, model_name: str) -> Optional[ModelMetadata]:
        """Get metadata for a model"""
        if model_name not in self.model_metadata:
            # Try to load from modelfile
            model_path = self.getModelPath(model_name)
            if model_path:
                model_dir = os.path.dirname(model_path)
                metadata = ModelFile.parseModelfile(model_dir)
                if metadata:
                    self.model_metadata[model_name] = metadata

        return self.model_metadata.get(model_name)

    def setCurrentModel(self, model_name: str) -> bool:
        """Set current model"""
        if model_name not in self.models_cache:
            self.discoverModels()

        if model_name not in self.models_cache:
            print(f"❌ Model not found: {model_name}")
            return False

        self.current_model_name = model_name
        print(f"✅ Current model set to: {model_name}")
        return True

    def getCurrentModel(self) -> Optional[str]:
        """Get current model name"""
        return self.current_model_name

    def getCurrentModelPath(self) -> Optional[str]:
        """Get current model path"""
        if not self.current_model_name:
            return None
        return self.getModelPath(self.current_model_name)


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
    def parseHfUrl(url: str) -> Tuple[Optional[str], Optional[str]]:
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

    def pullModel(
        self,
        hf_repo_url: str,
        model_name: Optional[str] = None,
        metadata: Optional[Dict] = None,
        system_prompt: str = "You are a helpful assistant.",
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> Tuple[bool, str]:
        """
        Pull model from HuggingFace repository

        Args:
            hf_repo_url: HuggingFace repository URL (https://huggingface.co/owner/repo or owner/repo)
            model_name: Custom name for the model (uses repo name if not provided)
            system_prompt: System prompt for the model
            metadata: Additional metadata dictionary
            progress_callback: Callback function for progress updates (receives DownloadProgress object)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Parse HF URL
            owner, repo = self.parseHfUrl(hf_repo_url)
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

            # Update progress: starting download
            if progress_callback:
                progress_callback(
                    DownloadProgress(
                        downloaded=0, total=0, filename=f"{owner}/{repo}", percent=0.0
                    )
                )

            # Use HuggingFace CLI to download with progress tracking
            # Assuming huggingface_hub is installed
            try:
                pass

                # Download all .rkllm files from the repo
                # First, we need to list files in the repo

                print(f"🔍 Scanning repository for .rkllm files...")

                # Update progress: scanning
                if progress_callback:
                    progress_callback(
                        DownloadProgress(
                            downloaded=0,
                            total=0,
                            filename="Scanning repository...",
                            percent=0.0,
                        )
                    )

                # Try using git lfs or huggingface_hub
                # For now, use huggingface-cli command with progress
                result = subprocess.Popen(
                    [
                        "hf",
                        "download",
                        f"{owner}/{repo}",
                        "--repo-type",
                        "model",
                        "--local-dir",
                        str(model_dir),
                    ],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                )

                # Track progress from output
                total_size = 0
                downloaded_size = 0

                for line in iter(result.stdout.readline, ""):
                    if not line:
                        break

                    print(line, end="")

                    # Parse download progress from hf output
                    # Example: "downloading to /path/file.rkllm (1.2 GB / 2.5 GB)"
                    if "downloading to" in line and "/" in line:
                        try:
                            # Extract sizes from output
                            parts = line.split("(")[1].split("/") if "(" in line else []
                            if len(parts) == 2:
                                down_str = parts[0].strip().split()[0]
                                total_str = parts[1].strip().split()[0]

                                # Parse size strings (convert to bytes)
                                def parse_size(size_str: str) -> int:
                                    multipliers = {
                                        "B": 1,
                                        "KB": 1024,
                                        "MB": 1024**2,
                                        "GB": 1024**3,
                                        "TB": 1024**4,
                                    }
                                    for unit, mult in multipliers.items():
                                        if unit in size_str:
                                            return int(
                                                float(size_str.replace(unit, "")) * mult
                                            )
                                    return 0

                                downloaded_size = parse_size(down_str)
                                total_size = parse_size(total_str)

                                # Update progress
                                if progress_callback and total_size > 0:
                                    progress_callback(
                                        DownloadProgress(
                                            downloaded=downloaded_size,
                                            total=total_size,
                                            filename=line.split("/")[-1]
                                            .split("(")[0]
                                            .strip(),
                                            percent=(
                                                (downloaded_size / total_size) * 100
                                                if total_size > 0
                                                else 0
                                            ),
                                        )
                                    )
                        except Exception:
                            pass  # Continue even if parsing fails

                result.wait()

                if result.returncode != 0:
                    return False, f"❌ Failed to pull model"

                # Update progress: complete
                if progress_callback:
                    progress_callback(
                        DownloadProgress(
                            downloaded=total_size,
                            total=total_size,
                            filename="Download complete",
                            percent=100.0,
                        )
                    )

                print(f"✅ Model pulled successfully")

            except ImportError:
                # Fallback to git clone if huggingface_hub not available
                print(f"⚠️  huggingface_hub not available, trying git clone...")

                if progress_callback:
                    progress_callback(
                        DownloadProgress(
                            downloaded=0,
                            total=0,
                            filename="Cloning repository...",
                            percent=0.0,
                        )
                    )

                hf_url = f"https://huggingface.co/{owner}/{repo}.git"
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", hf_url, str(model_dir)],
                    capture_output=True,
                    text=True,
                    timeout=3600,
                )

                if result.returncode != 0:
                    return False, f"❌ Failed to clone repository: {result.stderr}"

                print(f"✅ Model repository cloned successfully")

            # Create modelfile with metadata
            model_metadata = ModelMetadata(
                name=model_name,
                system_prompt=system_prompt,
                description=f"Model from: {owner}/{repo}",
            )

            # Add any additional metadata
            if metadata:
                for key, value in metadata.items():
                    if hasattr(model_metadata, key):
                        setattr(model_metadata, key, value)

            # Create modelfile
            if ModelFile.createModelfile(str(model_dir), model_metadata):
                print(f"✅ Created modelfile for: {model_name}")

            return True, f"✅ Model pulled successfully: {model_name}"

        except subprocess.TimeoutExpired:
            return False, "❌ Model pull timed out (>1 hour)"
        except Exception as e:
            return False, f"❌ Error pulling model: {str(e)}"

    def verifyModel(self, model_name: str) -> Tuple[bool, str]:
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

    def cleanupModel(self, model_handle: Any) -> bool:
        """
        Cleanup model resources

        Args:
            model_handle: Model handle to cleanup

        Returns:
            Success status
        """
        try:
            with self.lock:
                if model_handle and hasattr(model_handle, "release"):
                    model_handle.release()
                    print("✅ Model resources cleaned up")
                    return True
        except Exception as e:
            print(f"❌ Error cleaning up resources: {e}")

        return False

    def switchModel(self, old_model: Any, new_model: Any) -> bool:
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
                    if hasattr(old_model, "release"):
                        old_model.release()
                    if hasattr(old_model, "destroy"):
                        old_model.destroy()

                # Set new model as current
                self.current_model_handle = new_model

                print("✅ Model switched successfully")
                return True
        except Exception as e:
            print(f"❌ Error switching models: {e}")
            return False

    def getCurrentModel(self) -> Any:
        """Get current model handle"""
        return self.current_model_handle


# Convenience functions
def discoverModels(model_folder: str) -> Dict[str, str]:
    """Convenience function to discover models"""
    manager = ModelManager(model_folder)
    manager.discoverModels()
    return {name: info["path"] for name, info in manager.getAvailableModels().items()}


def getModelMetadata(model_folder: str, model_name: str) -> Optional[ModelMetadata]:
    """Convenience function to get model metadata"""
    manager = ModelManager(model_folder)
    return manager.getModelMetadata(model_name)


def pullModelFromHf(
    model_folder: str, hf_url: str, model_name: Optional[str] = None
) -> Tuple[bool, str]:
    """Convenience function to pull model from HuggingFace"""
    puller = ModelPuller(model_folder)
    return puller.pullModel(hf_url, model_name)
