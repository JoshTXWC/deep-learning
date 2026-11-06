# Gesture controls (barehands extension)

Jarvis does **not** replace [barehands](https://github.com/jaredrhod/barehands). When `gesture_controls` is enabled in `jarvis.json` and barehands is installed:

## Allowed gesture actions (configurable)

- Switch visualizer face / open Jarvis dashboard
- Navigate dashboard panels
- Dismiss noncritical notifications
- Trigger approved presentation cues already staged by the agent

## Hard rules

- Gestures alone **cannot** approve high-risk operations.
- Camera frames stay in the browser / local barehands process unless the user explicitly opts into an external vision API (default: off).
- `webcam_enabled` defaults to false; dashboard shows camera state.

Wire gestures by reading barehands state files the same way the voice ring already does — no new public ports.
