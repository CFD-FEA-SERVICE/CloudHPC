# cloudHPC MCP server

Run engineering simulations on [cloudHPC](https://cloudhpc.cloud) from Claude and
other MCP clients: inspect a local case, get vCPU/RAM advice, upload the folder,
launch, monitor and download the results.

Supported solvers: everything listed by cloudHPC (FDS, OpenFOAM, snappyHexMesh,
code_aster, CalculiX, OpenRadioss, SU2, ...). Resource advice follows the
[cloudHPC scalability rules](https://docs.cloudhpc.cloud/scalability/).

## Tools

| Tool | What it does | Mode |
|---|---|---|
| `inspect_case` | Detect solver and model size of a local folder (FDS meshes/MPI groups, OpenFOAM cells, CalculiX nodes, ...) | local |
| `upload_folder` | tar.gz the folder content and upload it to storage | local |
| `download_results` | Download result archives and extract them locally | local |
| `list_solvers` | Available solvers, grouped by family | both |
| `list_machine_options` | vCPU counts and RAM/instance types | both |
| `suggest_resources` | vCPU + RAM type recommendation with reasoning | both |
| `list_storage`, `list_results` | Browse storage / result archives | both |
| `get_upload_link`, `get_download_link` | Signed URLs + ready `curl` commands | both |
| `launch_simulation` | Launch a run (**asks for confirmation**) | both |
| `list_simulations`, `get_simulation`, `wait_for_simulation` | Monitor runs | both |
| `sync_simulation` | Upload partial results of a running job | both |
| `stop_simulation` | Soft/hard stop (**asks for confirmation**) | both |
| `delete_storage` | Delete file/folder (**asks for confirmation**) | both |
| `open_remote_desktop` | Browser remote-desktop link of a running job | both |
| `api_usage` | Rate limits and calls used | both |

Actions that cost money or delete data return a summary first and run only when
called again with `confirm=true`.

## API key

Your key is on your cloudHPC profile page. Treat it like a password: it gives
full access to your account.

- **local mode**: `CLOUDHPC_APIKEY` environment variable, or the file
  `~/.cfscloudhpc/apikey` used by `cloudHPCexec`.
- **remote mode**: sent by the client with every request as `X-API-Key: <key>`
  or `Authorization: Bearer <key>`. The server stores nothing.

## Local mode (recommended for your own case folders)

```bash
pip install git+https://github.com/CFD-FEA-SERVICE/cloudhpc-mcp
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "cloudhpc": {
      "command": "cloudhpc-mcp",
      "env": { "CLOUDHPC_APIKEY": "your-key" }
    }
  }
}
```

Claude Code:

```bash
claude mcp add cloudhpc -e CLOUDHPC_APIKEY=your-key -- cloudhpc-mcp
```

Then ask e.g. *"Run the FDS case in ~/cases/warehouse on cloudHPC and download
the results when it finishes."*

## Remote mode (hosted)

```bash
CLOUDHPC_MCP_MODE=remote PORT=8080 cloudhpc-mcp     # endpoint: http://host:8080/mcp
```

Client configuration (e.g. Claude Code):

```bash
claude mcp add --transport http cloudhpc https://mcp.cloudhpc.cloud/mcp \
  --header "X-API-Key: your-key"
```

In remote mode the server cannot read files on your computer: uploads and
downloads use the signed links returned by `get_upload_link` / `get_download_link`.

### Deploy on Google Cloud Run

```bash
gcloud run deploy cloudhpc-mcp \
  --project cfd-fea-service-cloud --region europe-west4 \
  --source . --allow-unauthenticated \
  --min-instances 0 --max-instances 5 --memory 512Mi --timeout 3600
```

`--allow-unauthenticated` is correct here: every tool call is authenticated by
the cloudHPC API with the user's own key. `--timeout 3600` lets
`wait_for_simulation` keep a request open.

## Configuration

| Variable | Default | |
|---|---|---|
| `CLOUDHPC_MCP_MODE` | `local` | `local` (stdio) or `remote` (streamable HTTP) |
| `CLOUDHPC_API_URL` | `https://cloud.cfdfeaservice.it/api/v2` | Staging: `https://testcloud.cfdfeaservice.it/api/v2` |
| `CLOUDHPC_APIKEY` | – | local mode only |
| `HOST` / `PORT` | `0.0.0.0` / `8080` | remote mode |

## Development

```bash
pip install -e ".[test]"
pytest                                   # offline tests, mocked API
CLOUDHPC_APIKEY=<staging key> python3 scripts/staging_e2e.py --cleanup
```

## Notes

- Storage files are deleted automatically after 60 days.
- API rate limits: 100 calls/hour (free), 500/hour (full accounts). The server
  reads the `X-RateLimit-*` headers and stops before exceeding them.
- Upload layout: the content of the case folder is archived at the root of
  `upload.tar.gz` and uploaded into a storage folder with the case name
  (method 2 of the [storage docs](https://docs.cloudhpc.cloud/storage/)).

## License

Apache-2.0
