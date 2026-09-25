from pythonforandroid.recipes.pygame import Pygame2Recipe as UpstreamPygame2Recipe

class Pygame2Recipe(UpstreamPygame2Recipe):
    hostpython_prerequisites = ["Cython==0.29.34"]

recipe = Pygame2Recipe()
