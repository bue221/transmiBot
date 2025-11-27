.PHONY: install run docker-build docker-run deploy clean adk-web

install:
	uv sync --python 3.12

run:
	uv run python -m app.main

docker-build:
	docker build -t transmibot:latest .

docker-run:
	docker run -d \
  		--restart unless-stopped \
  		--name transmibot_instance \
  		--env-file .env \
  		-p 8080:8080 \
  		transmibot:latest

deploy: docker-build
	@echo "Stopping and removing existing container if it exists..."
	-docker stop transmibot_instance 2>/dev/null || true
	-docker rm transmibot_instance 2>/dev/null || true
	@echo "Starting new container..."
	$(MAKE) docker-run

clean:
	rm -rf .venv __pycache__

adk-web:
	cd $(CURDIR)/src/app/agents && uv run adk web
