"""The assistant worker: the voice features that are not assessments.

Help (FAQ answers, optionally with on-screen guidance), onboarding (scene by
scene coaching), dashboard coaching and the consulting-doctor role. Sessions
are bootstrapped from the backend that dispatched them, which renders any
data-dependent instructions; the pure templates (help, onboarding) live here
because onboarding rebuilds its instructions mid-session.

This package never imports the assessment engine's runtime or evaluation.
"""
