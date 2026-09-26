from pythonforandroid.recipes.pygame import Pygame2Recipe as UpstreamPygame2Recipe


class Pygame2Recipe(UpstreamPygame2Recipe):
    # pygame's setup.py invokes Cython during build_ext. p4a's host-Python
    # is isolated from the GitHub Actions Python, so install Cython there.
    hostpython_prerequisites = ["Cython==0.29.34"]


recipe = Pygame2Recipe()
