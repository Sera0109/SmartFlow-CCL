# Testing

From `backend`, create a virtual environment and run `pytest -q`. The tests cover health, coordinate validation, assignment scoring, invalid IDs, and invalid transitions without AWS credentials or a live database.

For a complete local demonstration, start MySQL, load `schema.sql`, run FastAPI and the worker in separate terminals, and start Vite. Place an order, wait for the worker to assign it, move it out for delivery, upload an image proof, open the proof URL, and refresh Admin Analytics.
