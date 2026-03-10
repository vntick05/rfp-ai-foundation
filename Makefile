SHELL := /bin/bash

COMPOSE_FILES := -f docker-compose.yml
GPU_COMPOSE_FILES := -f docker-compose.yml -f docker-compose.gpu.yml

.PHONY: up up-gpu down logs ps config config-gpu check portainer-url

up:
	docker compose $(COMPOSE_FILES) up -d --build

up-gpu:
	docker compose $(GPU_COMPOSE_FILES) up -d --build

down:
	docker compose $(GPU_COMPOSE_FILES) down

logs:
	docker compose $(GPU_COMPOSE_FILES) logs -f --tail=100

ps:
	docker compose $(GPU_COMPOSE_FILES) ps

config:
	docker compose $(COMPOSE_FILES) config

config-gpu:
	docker compose $(GPU_COMPOSE_FILES) config

check:
	./scripts/check.sh

portainer-url:
	./scripts/portainer-url.sh
