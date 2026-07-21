"""
Utility functions for the Video Watermark Remover application.

This module can contain helper functions انتخابات_related to:
- File operations (e.g., validating paths, creating directories)
- String manipulation
- Common image processing tasks not specific to AI models
- UI helper functions (e.g., showing message boxes)
- etc.
"""

import os

# import platform # For platform-specific utilities


def ensure_directory_exists(dir_path):
    """
    Ensures that a directory exists. If not, it creates it.
    Returns True if directory exists or was created, False otherwise.
    """
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
            # print(f"Directory created: {dir_path}") # Optional: log this
            return True
        except OSError:
            # print(f"Error creating directory {dir_path}: {e}") # Optional: log this
            return False
    return True


def get_file_basename(file_path):
    """Returns the basename of a file without its extension."""
    if not file_path:
        return ""
    return os.path.splitext(os.path.basename(file_path))[0]


def get_file_extension(file_path):
    """Returns the extension of a file (e.g., '.mp4')."""
    if not file_path:
        return ""
    return os.path.splitext(file_path)[1]


# Example: A function to format time duration
def format_duration(seconds):
    """Converts seconds into a HH:MM:SS string format."""
    if seconds < 0:
        return "00:00:00"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
