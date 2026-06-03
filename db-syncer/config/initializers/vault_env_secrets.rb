# Read secrets from main app config.
VaultEnvSecrets.template_path = Rails.root.join("../config/vault_secrets.json.tmpl")

# Read Vault secrets into environment variables for local development (in
# production, these will be handled via Kubernetes secrets).
VaultEnvSecrets.enabled = (ENV["LOAD_VAULT_ENV_SECRETS"] == "true")
