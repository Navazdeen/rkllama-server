from dataclasses import asdict, dataclass
from typing import Callable, Dict


@dataclass
class DownloadProgress:
    """Download progress tracking"""

    downloaded: int = 0
    total: int = 0
    filename: str = ""
    percent: float = 0.0

    def format_size(self, size_bytes: int) -> str:
        """Format bytes to human-readable format"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"

    def get_progress_bar(self, length: int = 30) -> str:
        """Generate text progress bar"""
        if self.total == 0:
            return "⏳ Waiting..."

        filled = int(length * self.downloaded / self.total)
        bar = "█" * filled + "░" * (length - filled)
        return f"[{bar}] {self.percent:.1f}%"

    def get_status_text(self) -> str:
        """Get formatted status text"""
        downloaded_fmt = self.format_size(self.downloaded)
        total_fmt = self.format_size(self.total)

        if self.total == 0:
            return f"⏳ Scanning: {self.filename}"

        return f"{self.get_progress_bar()}\n{downloaded_fmt} / {total_fmt} ({self.percent:.1f}%)"


class ProgressTracker:
    """Track download progress with callbacks"""

    def __init__(
        self, progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ):
        """
        Initialize progress tracker

        Args:
            progress_callback: Callback function called with DownloadProgress object
        """
        self.progress = DownloadProgress()
        self.progress_callback = progress_callback
        self.lock = threading.Lock()

    def update(self, downloaded: int, total: int, filename: str = ""):
        """Update progress"""
        with self.lock:
            self.progress.downloaded = downloaded
            self.progress.total = total
            self.progress.filename = filename

            if total > 0:
                self.progress.percent = (downloaded / total) * 100
            else:
                self.progress.percent = 0.0

            if self.progress_callback:
                self.progress_callback(self.progress)

    def get_current_progress(self) -> DownloadProgress:
        """Get current progress"""
        with self.lock:
            return DownloadProgress(
                downloaded=self.progress.downloaded,
                total=self.progress.total,
                filename=self.progress.filename,
                percent=self.progress.percent,
            )


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
    def from_dict(cls, data: Dict) -> "ModelMetadata":
        """Create from dictionary"""
        return cls(**data)
