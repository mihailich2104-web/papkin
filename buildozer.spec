[app]
title = Neon Defender
package.name = neondefender
package.domain = org.neondefender
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ico
source.include_patterns = main.py,game.py,network.py,icon.ico
version = 2.0.0
requirements = python3==3.11.6,hostpython3==3.11.6,pygame==2.5.2
orientation = landscape
fullscreen = 1
android.presplash_color = #05060e
icon.filename = %(source.dir)s/icon.ico

android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 35
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True
android.enable_androidx = True
android.accept_sdk_license = True

p4a.branch = master
p4a.local_recipes = ./p4a-recipes

[buildozer]
log_level = 2
warn_on_root = 1
