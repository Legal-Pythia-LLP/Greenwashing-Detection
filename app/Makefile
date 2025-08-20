CONFIG_DIR := ./configs

.PHONY: docker-pg-rm
docker-pg-rm:
	@docker run --rm \
		-p 5432:5432 \
		-e POSTGRES_PASSWORD=postgres \
		-v ./docker/builds/pg/includes/:/docker-entrypoint-initdb.d/ \
		postgres:alpine

.PHONY: docker-redis-rm
docker-redis-rm:
	@docker run --rm \
		-p 6379:6379 \
		redis:alpine

dev:
	uv run fastapi dev ./main.py

initial-gcp-deploy:
	gcloud run deploy demos-green-washing-analysis-api \
		--image=europe-west2-docker.pkg.dev/legal-pythia-external/demos/green-washing-analysis/green-washing-analysis-api:latest \
		--allow-unauthenticated \
		--description="Demo Green Washing Analysis API" \
		--min-instances=1 \
		--max-instances=1 \
		--region=europe-west1 \
		--timeout=5m \
		--port 8080 \
		--labels="type=external,app=demos-green-washing-analysis-api" \
		--verbosity=info \
		--env-vars-file="$(CONFIG_DIR)/prod/env/green-washing-analysis-env.yaml"

version ?= $(shell git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0")
profile ?= dev
profile_with_identifier := $(if $(profile),$(profile)+,)

.PHONY: gcp-build
gcp-build: 
	gcloud builds submit \
		--config ./infra/gcp/cloud-build.yaml \
		--substitutions="_VERSION=$(version),_VERSION_REVISION=$(profile_with_identifier)$(shell git rev-parse --short HEAD)" \
		--timeout 30m \
		--ignore-file=./.gcloudignore \
		--project legal-pythia-external \
		--region=europe-west2

.PHONY: gcp-deploy
gcp-deploy:
	gcloud run deploy demos-green-washing-analysis-api \
		--image=europe-west2-docker.pkg.dev/legal-pythia-external/demos/green-washing-analysis/green-washing-analysis-api:latest \
		--allow-unauthenticated \
		--region=europe-west1 \
		--port 8080 \
		--timeout=10m

gcp-build-and-deploy: gcp-build gcp-deploy
