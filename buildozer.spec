[app]
title = Tilt Arcade
package.name = tiltarcade
package.domain = io.github.yuvaingarg
source.dir = .
source.include_exts = py,png
source.exclude_dirs = MarbleController,case,bin,android,.github,.buildozer,build-s3,build-p2,__pycache__
source.exclude_patterns = screenshot.png
version = 1.0.0
icon.filename = %(source.dir)s/icon.png
# bleak comes from its own python-for-android recipe (android/recipes/bleak)
requirements = python3==3.13.5,hostpython3==3.13.5,pygame,pyjnius==1.9.0,bleak
orientation = landscape
fullscreen = 1
android.permissions = BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_SCAN, BLUETOOTH_CONNECT, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION
android.api = 34
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
p4a.bootstrap = sdl2
p4a.local_recipes = android/recipes
android.debug_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 0
