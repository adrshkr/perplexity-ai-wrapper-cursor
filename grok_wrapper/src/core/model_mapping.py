"""
Model name mapping for Grok UI models to API parameters
"""
from typing import Dict, Tuple, Optional

# Mapping from UI model names to (model_name, model_mode) tuples
MODEL_MAPPING: Dict[str, Tuple[str, str]] = {
    # UI Model Name -> (API model_name, API model_mode)
    "auto": ("grok-4", "MODEL_MODE_BALANCED"),  # Auto chooses Fast or Expert
    "fast": ("grok-4", "MODEL_MODE_FUN"),  # Quick responses
    "expert": ("grok-4", "MODEL_MODE_EXPERT"),  # Thinks hard
    "grok-4-fast": ("grok-4-fast", "MODEL_MODE_FUN"),  # Grok 4 Fast Beta
    "heavy": ("grok-4", "MODEL_MODE_EXPERT"),  # Team of experts (uses expert mode)
    
    # New models (Grok 4.1 series)
    "grok-4.1": ("grok-4.1", "MODEL_MODE_EXPERT"),  # Grok 4.1
    "grok-4.1-think": ("grok-4.1", "MODEL_MODE_EXPERT"),  # Grok 4.1 Think (uses expert mode)
    "grok-4-1": ("grok-4.1", "MODEL_MODE_EXPERT"),  # Alternative naming
    "grok-4-1-think": ("grok-4.1", "MODEL_MODE_EXPERT"),  # Alternative naming
    
    # Legacy model names (for backward compatibility)
    "grok-4": ("grok-4", "MODEL_MODE_EXPERT"),
    "grok-2": ("grok-2", "MODEL_MODE_EXPERT"),
    "grok-beta": ("grok-beta", "MODEL_MODE_EXPERT"),
}

# UI model display names (for user-friendly output)
MODEL_DISPLAY_NAMES: Dict[str, str] = {
    "auto": "Auto (Chooses Fast or Expert)",
    "fast": "Fast (Quick responses)",
    "expert": "Expert (Thinks hard)",
    "grok-4-fast": "Grok 4 Fast (Beta)",
    "heavy": "Heavy (Team of experts)",
    "grok-4.1": "Grok 4.1",
    "grok-4.1-think": "Grok 4.1 Think",
    "grok-4-1": "Grok 4.1",
    "grok-4-1-think": "Grok 4.1 Think",
    "grok-4": "Grok-4",
    "grok-2": "Grok-2",
    "grok-beta": "Grok Beta",
}


def get_model_params(model: str) -> Tuple[str, str]:
    """
    Get API parameters for a model name
    
    Args:
        model: Model name (e.g., "auto", "fast", "expert", "grok-4")
    
    Returns:
        Tuple of (model_name, model_mode)
    """
    model_lower = model.lower().strip()
    
    if model_lower in MODEL_MAPPING:
        return MODEL_MAPPING[model_lower]
    
    # Default to grok-4 with expert mode
    return ("grok-4", "MODEL_MODE_EXPERT")


def get_model_display_name(model: str) -> str:
    """Get user-friendly display name for a model"""
    model_lower = model.lower().strip()
    return MODEL_DISPLAY_NAMES.get(model_lower, model)


def list_available_models() -> list:
    """List all available model names"""
    return list(MODEL_MAPPING.keys())

