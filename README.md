# Cloudflare DNS Management — IaC + GitOps with octoDNS

Manage your Cloudflare DNS records using YAML files. All changes are proposed and reviewed via pull requests.

## How to Add or Update DNS Records

1.  **Find the correct file:** DNS records are organized in YAML files under the `zones/` directory. For example, records for `example.com` are in `zones/example.com/example.com.yml`. For subdomains, find or create `zones/example.com/sub.example.com.yml`.
2.  **Edit the file:** Make your desired changes to the YAML file. You can do this directly on GitHub.
3.  **Open a Pull Request:** Propose your changes by opening a pull request.
4.  **Review and Merge:** Your pull request will be automatically validated by our CI system. A maintainer will then review and merge your changes. Once merged, the changes will be deployed automatically.

### Example Record

Here is an example of an A record in a YAML file:

```yaml
"www":
  - ttl: 300
    type: 'A'
    value: '192.0.2.1'
```

Please ensure your changes conform to the existing structure and [octoDNS record syntax](https://octodns.readthedocs.io/en/latest/records.html).

## Maintainer: Set up Cloudflare API Token

To enable DNS management through automated workflows, you'll need to create a Cloudflare API token with specific permissions.

1.  **Log in to Cloudflare:** Go to your Cloudflare dashboard.
2.  **Go to API Tokens:** Navigate to "My Profile" > "API Tokens".
3.  **Create a Custom Token:**
    *   Grant the following permissions:
        *   **Zone:** `DNS`: `Edit`
    *   Set the zone resources to "All zones" or select the specific zones you want to manage.
4.  **Set the Token as a Secret:** In your GitHub repository, go to "Settings" > "Secrets" and add a new secret with the name `CLOUDFLARE_API_TOKEN`.
5.  **Add records:** You can now add or update DNS records in the `zones/` directory after removing `example.com` zone. Be sure to first pre-create records for existing domains and manually verify the changes before merging and deploying.

### Useful commands

```bash
# Generate compiled config for all zones
python scripts/build_config.py

# Validate syntax and semantics locally
octodns-validate --config-file compiled.config.yml --all

# Preview changes (requires CLOUDFLARE_API_TOKEN)
octodns-sync --config-file compiled.config.yml

# Apply changes (requires CLOUDFLARE_API_TOKEN)
octodns-sync --config-file compiled.config.yml --doit
```

## Contribution Guidelines

For details on how to set up the project locally for development or to understand the validation and build process, please see [CONTRIBUTING.md](CONTRIBUTING.md).