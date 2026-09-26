# Neon Defender Android build

This archive is configured for GitHub Actions Android APK builds.
The Android workflow deliberately clears Buildozer caches so stale NDK/p4a state cannot leak between builds.
python-for-android 2026.05.09 is used. `hostpython3` is a normal internal dependency of p4a and is not a user-supplied requirement.
