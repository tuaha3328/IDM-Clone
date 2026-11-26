import re
from pathlib import Path


_FOLDER_BY_EXTENSION = {
    **dict.fromkeys(
        {
            ".abw", ".csv", ".djv", ".djvu", ".doc", ".docm", ".docx",
            ".dot", ".dotm", ".dotx", ".epub", ".fb2", ".fodt", ".htm",
            ".html", ".json", ".key", ".latex", ".log", ".markdown", ".md",
            ".mobi", ".numbers", ".odf", ".odp", ".ods", ".odt", ".otp",
            ".ots", ".ott", ".pages", ".pdf", ".pot", ".potm", ".potx",
            ".pps", ".ppsm", ".ppsx", ".ppt", ".pptm", ".pptx", ".pub",
            ".rtf", ".tex", ".tsv", ".txt", ".wpd", ".wps", ".xhtml",
            ".xla", ".xls", ".xlsb", ".xlsm", ".xlsx", ".xlt", ".xltm",
            ".xltx", ".xml", ".yaml", ".yml",
        },
        "Documents",
    ),
    **dict.fromkeys(
        {
            ".3gp", ".avi", ".flv", ".m4v", ".mkv", ".mov", ".mp4",
            ".mpeg", ".mpg", ".ogv", ".ts", ".webm", ".wmv", ".aac",
            ".aiff", ".flac", ".m4a", ".mp3", ".ogg", ".opus", ".wav",
            ".wma",
        },
        "Video",
    ),
    **dict.fromkeys(
        {
            ".aab", ".appimage", ".appx", ".appxbundle", ".apk", ".bat",
            ".bin", ".cmd", ".com", ".deb", ".dmg", ".exe", ".flatpak",
            ".jar", ".msi", ".msix", ".msixbundle", ".msp", ".msu", ".pkg",
            ".ps1", ".rpm", ".run", ".scr", ".sh", ".sys",
        },
        "Programs",
    ),
    **dict.fromkeys(
        {
            ".001", ".7z", ".7zip", ".ace", ".alz", ".arc", ".arj", ".br",
            ".bz2", ".cab", ".cpio", ".gz", ".gzip", ".iso", ".lha", ".lzh",
            ".lz", ".lz4", ".lzma", ".lzo", ".rar", ".shar", ".sit", ".sitx",
            ".tar", ".taz", ".tbz", ".tbz2", ".tgz", ".tlz", ".txz", ".tzst",
            ".wim", ".xar", ".xz", ".z", ".zip", ".zipx", ".zst", ".zstd",
        },
        "Compressed",
    ),
}


def _get_extension(filename):
    extension = Path(filename).suffix.lower()
    if re.fullmatch(r"\.(?:\d{3}|[rz]\d{2})", extension):
        return ".001"
    return extension


def get_download_directory(filename):
    """Create and return a type-specific folder under the current user's Downloads."""
    extension = filename.lower()
    if extension not in _FOLDER_BY_EXTENSION:
        extension = _get_extension(filename)
    subfolder = _FOLDER_BY_EXTENSION.get(extension)

    destination = Path.home() / "Downloads"
    if subfolder:
        destination /= subfolder
    destination.mkdir(parents=True, exist_ok=True)
    return str(destination)


def get_download_path(filename):
    """Build a destination path using the current user's Downloads folder."""
    return str(Path(get_download_directory(filename)) / Path(filename).name)
