"""The assessment worker: runs one attempt's interaction on LiveKit.

Job metadata carries an attempt id, a backend label and a candidate
reference. The worker resolves the label through ``voice_infra``'s
registry, fetches the attempt from that backend's bootstrap route (the
instructions arrive already rendered), waits for the candidate, runs the
interaction through the engine's runtime with a LiveKit adapter, streams
every turn back and delivers the transcript exactly once. It never scores:
the backend that receives the transcript runs the evaluator.

The worker knows nothing about products, station shapes or prompts.
"""
