resource "google_cloud_run_domain_mapping" "green_washing_analysis_api_domain_mapping" {
  location = "europe-west1"
  name     = "api.gwa.demos.legalpythia.com"

  metadata {
    namespace = var.project
  }

  spec {
    route_name = "demos-green-washing-analysis-api"
  }
}
