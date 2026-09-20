"""Start the agent in the Gunicorn child, without waiting for an HTTP request."""


def post_worker_init(worker):
    from hosting.supervisor import _start_once

    _start_once()
