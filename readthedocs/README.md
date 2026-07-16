# readthedocs — online documentation sources

MkDocs sources of the cloudHPC user documentation published at **https://docs.cloudhpc.cloud**.

## Content

- `mkdocs.yml` — site configuration and navigation (user guide, API reference, tools, tutorials links)
- `docs/` — Markdown pages: user guide (`index.md`, `account.md`, `storage.md`, `simulation.md`, `monitor.md`, `scalability.md`, `executions.md`, `errors.md`, `billing.md`, `tools.md`), API reference (`API-INTRODUCTION.md`, `API-v1.md`, `API-v2.md`, `APIKEY.md`), plus images (`images/`, `img/`) and the site `CNAME`

## Building locally

```bash
pip install mkdocs
cd readthedocs
mkdocs serve      # live preview at http://127.0.0.1:8000
mkdocs build      # static site in site/
```
