API_PORT=8080

.PHONEY: generate-requirements
generate-requirements:
	pipenv requirements > requirements.txt

.PHONEY: generate-dev-requirements
generate-dev-requirements:
	pipenv requirements --dev > requirements-dev.txt

.PHONEY: generate-all-requirements
generate-all-requirements: generate-requirements generate-dev-requirements

.PHONEY: dev
dev:
	source .env.local && pipenv run fastapi dev ./main.py --port 8080

.PHONEY: docker-build
docker-build: generate-requirements generate-all-protos
	docker build \
		--file ./Dockerfile \
		--tag legal-pythia/bma-api:$(shell git rev-parse --abbrev-ref HEAD)-latest \
		--tag legal-pythia/bma-api:$(shell git rev-parse --abbrev-ref HEAD)-$(shell git rev-parse --short HEAD) \
		.

.PHONEY: docker-run
docker-run: docker-build
	docker rm -f "bma-api-$(shell git rev-parse --abbrev-ref HEAD)-$(shell git rev-parse --short HEAD)"
	docker run \
		--name "bma-api-$(shell git rev-parse --abbrev-ref HEAD)-$(shell git rev-parse --short HEAD)" \
		--publish "$(API_PORT):$(API_PORT)" \
		--env "PORT=$(API_PORT)" \
		legal-pythia/bma-api:$(shell git rev-parse --abbrev-ref HEAD)-$(shell git rev-parse --short HEAD)

.PHONY: gcp-build
gcp-build:
	gcloud builds submit \
		--config ./infra/cloud-build.yaml \
		--timeout 30m \
		--ignore-file=./.gcloudignore \
		--project legal-pythia-external \
		--region=europe-west2 \
		--machine-type=e2-highcpu-8

# --image=europe-west2-docker.pkg.dev/legal-pythia-external/demos/bma-web:latest
.PHONY: gcp-deploy
gcp-deploy:
	gcloud run deploy bma-web-demo \
		--source . \
		--allow-unauthenticated \
		--description="BMA Demo" \
		--region=europe-west1 \
		--timeout=10m \
		--labels="type=internal,app=demos-bma"

gcp-build-and-deploy: gcp-build gcp-deploy
