from app import create_app

# cPanel / Phusion Passenger expects a WSGI callable named `application`.
# We deliberately avoid starting the background scheduler here; run background
# jobs via cron or a separate process in production.
application = create_app()
