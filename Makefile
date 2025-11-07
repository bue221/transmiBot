.PHONY: install run docker-build docker-run clean

install:
	uv sync --python 3.12

run:
	uv run python -m app.main

docker-build:
	docker build -t transmibot:latest .

docker-run:
	docker run --rm \
		-e TELEGRAM_BOT_TOKEN \
		-e GOOGLE_API_KEY \
		-p 8080:8080 \
		transmibot:latest

clean:
	rm -rf .venv __pycache__
