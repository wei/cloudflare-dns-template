**Contributing Guidelines (DNS Changes)**

Overview
- This repo manages Cloudflare DNS with octoDNS in a GitOps flow.
- Architecture and flow are documented below.

Branch + PR Flow
- Create a feature branch; make changes only under `zones/`.
- Keep one logical change per PR (e.g., add a record; add a zone).
- Include a short description and rationale in the PR body.

Local Setup (optional)
- Requires Python 3.11+.
- Install deps: `pip install -r requirements.txt`.
- Build config: `python scripts/build_config.py` (writes `compiled/` and `compiled.config.yml`).
- Validate: `octodns-validate --config-file compiled.config.yml --all`.
- Preview diff (optional): `CLOUDFLARE_API_TOKEN=... octodns-sync --config-file compiled.config.yml`.

Credentials
- CI and local preview use `CLOUDFLARE_API_TOKEN` with DNS:Edit on target zones.
- In GitHub Actions, set secret `CLOUDFLARE_API_TOKEN`; workflows map it to the env var.

Repository Structure
- `zones/`: one folder per root zone (e.g., `zones/example.com/`).
- `zones/<zone>/<zone>.yml`: apex zone file (required per zone).
- `zones/<zone>/*.yml`: optional subdomain files for organization.
- `scripts/build_config.py`: compiles zones and emits `compiled.config.yml`.
- `compiled/`: generated YamlProvider zone files (git-ignored).
- Workflows: validate PRs, deploy on merge, rollback to any git ref.

Zone File Rules
- Apex file per domain, e.g., `zones/example.com/example.com.yml`.
- You may create per-subdomain files (e.g., `sub.example.com.yml`, `api.example.com.yml`). The build merges these into the apex so all records deploy to the same Cloudflare Zone ID.
- For delegated sub-zones, add `NS` records at the subdomain label in the parent and manage the delegated zone separately (do not model both parent and delegated child records here).
- Files may live in nested folders under `zones/`.
- Keep TTLs and record ordering stable to reduce diff noise (octoDNS may reorder).

Record Tips
- Use FQDNs with trailing dots for target values when applicable.
- CNAME cannot coexist with other records at the same name.
- MX requires `preference` (aka priority); SRV requires `priority`, `weight`, `port`, `target`.
- TXT values may be arrays (`values:`) or a single `value:`.
- For NS delegation of subzones, define `type: NS` under the delegated label.

Validation and CI
- Every PR runs `octodns-validate`.
- For internal PRs (secrets available), CI also runs a Cloudflare dry-run and uploads the plan artifact.

Merging and Deploy
- After approval, merging to `main` deploys automatically to Cloudflare.
- If deployment fails, check the workflow logs for error output.

Rollback
- Use the Rollback workflow (`Actions` → `Rollback DNS`) and supply a commit SHA or tag.
- The workflow checks out that ref and syncs it to Cloudflare.

Adding a New Zone
- Create `zones/example.com/example.com.yml` with initial records.
- Create `zones/example.com/<sub>.example.com.yml` files for subdomains.
- No config changes are required; the build auto-discovers new zones.

Operational Notes
- Cloudflare handles apex CNAME-style flattening automatically.
- Require fully qualified targets with trailing dots (e.g., `mx1.example.email.`).
- Policy: Single Cloudflare zone per root domain; subdomain files are merged into the apex.

Security
- Do not commit secrets; use GitHub secret `CLOUDFLARE_API_TOKEN`.
- PRs from forks do not have access to secrets and will skip the Cloudflare diff step.

**Architecture and Flow**

- Zones live under `zones/` in folders named after the apex domain (e.g., `zones/example.com/`).
- Each zone folder contains an apex file (`example.com.yml`) and subdomain files (e.g., `sub.example.com.yml`, `api.example.com.yml`).
- The build step compiles all zones and emits files under `compiled/` plus a single `compiled.config.yml` used by octoDNS.

Compilation Details
- Script: `python scripts/build_config.py`.
- Discovers zone directories under `zones/`.
- Loads the apex file as the base for the zone.
- For each subdomain file, remaps record names into the apex space at compile time:
  - `""` (apex) in `sub.example.com.yml` becomes `sub` in the compiled apex.
  - `www` in `sub.example.com.yml` becomes `www.sub` in the compiled apex.
- Deduplicates and stably sorts records to minimize diff noise.
- Writes one compiled YAML file per zone to `compiled/`.

octoDNS Config
- `compiled.config.yml` is generated on every build.
- Providers:
  - `yaml.YamlProvider` points at `compiled/` as the source of truth.
  - `octodns_cloudflare.CloudflareProvider` applies changes to Cloudflare using `CLOUDFLARE_API_TOKEN`.
- Zones mapping uses a wildcard (`"*"`) so any discovered zone is synced.

Workflows
- Validate PRs: runs `octodns-validate`. For internal PRs, also runs a Cloudflare dry-run and attaches the plan.
- Deploy on merge: runs `octodns-sync --doit` with the generated `compiled.config.yml`.
- Rollback: checks out a specified commit or tag and syncs that state to Cloudflare.

Notes
- Only one Cloudflare Zone ID per apex domain; subdomain files are organizational and compiled into the apex.
- For delegated sub-zones, add `NS` records at the subdomain label in the parent zone and manage the child separately.
