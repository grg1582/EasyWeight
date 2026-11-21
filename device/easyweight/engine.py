"""Feeds one video frame's pose landmarks into a Workout. Pure Python, so the
live app, the replay tool and the tests all count reps the same way."""
from . import config as cfg
from .counter import Workout
from .geometry import elbow_angle, joint_height, mouth_distance, shoulder_angle


class Engine:
    def __init__(self):
        self.workout = Workout()
        self.last_seen = None  # time someone was last in front of the mirror

    def step(self, landmarks, width, height, now):
        """Process one frame. landmarks is the list of 33 pose landmarks, or None
        when nobody is seen. width and height are the frame's size in pixels, now
        is the time in seconds. Returns True when a rep was counted"""
        workout = self.workout
        if self.last_seen is None:
            self.last_seen = now
        counted = False

        # Every exercise is watched on both arms. A raise must keep the elbow
        # fairly straight, so a curl or a drink can't count as one, and stay
        # below shoulder RAISE_MAX_ANGLE, so a press can't either
        for side in cfg.ARMS:
            elbow = elbow_angle(landmarks, side, width, height) if landmarks else None
            shoulder = shoulder_angle(landmarks, side, width, height) if landmarks else None
            wrist = joint_height(landmarks, side, 2, width, height) if landmarks else None
            elbow_up = joint_height(landmarks, side, 1, width, height) if landmarks else None
            mouth = mouth_distance(landmarks, side, width, height) if elbow is not None else None
            raise_ok = (elbow is not None and elbow > cfg.RAISE_MIN_ELBOW
                        and shoulder is not None and shoulder < cfg.RAISE_MAX_ANGLE)
            for exercise, angle, form_ok in (("curl", elbow, True),
                                             ("raise", shoulder, raise_ok),
                                             ("press", wrist, True)):
                counter = workout.counters[exercise][side]
                if (counter.update(angle, mouth, form_ok, wrist, elbow_up)
                        and workout.add_rep(now, exercise, counter)):
                    counted = True
        if workout.check_pending(now):
            counted = True

        # Nobody in front of the mirror for a while, or a rest that went on too
        # long: start fresh
        if landmarks:
            self.last_seen = now
        elif now - self.last_seen > cfg.AWAY_RESET_SECONDS:
            workout.reset()
        if workout.resting(now) and workout.rest_time(now) > cfg.MAX_REST_SECONDS:
            workout.reset()
        return counted

    def reset(self):
        self.workout.reset()
