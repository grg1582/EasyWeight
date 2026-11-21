"""EasyWeight: a rep counter for a smart mirror.

The package is split by job, so each part can be used and tested on its own:

    config     tuning constants
    geometry   angles and distances from pose landmarks (pure Python)
    counter    rep and set logic: ArmCounter and Workout (pure Python)
    engine     feeds one frame of landmarks into a Workout (pure Python)
    recording  saves and loads landmark recordings (pure Python)
    pose       MediaPipe pose model
    hud        drawing the mirror display
    app        camera, window and main loop
    replay     runs a recording through the engine, no camera needed
"""

__version__ = "0.2.0"
