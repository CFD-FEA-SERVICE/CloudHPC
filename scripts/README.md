# scripts — cluster execution scripts (open-source versions)

Open-source versions of the execution scripts used on the cloudHPC cluster to run the solvers. They show exactly how each solver is launched on the platform, and can be reused to replicate the same behaviour on your own machine (see the "Installation" section of the root README and the repository [releases](https://github.com/CFD-FEA-SERVICE/CloudHPC/releases)).

## Content

| File | Solver | Description |
|---|---|---|
| `codeAster-13.6` | code_aster 13.6 | Bash script that locates the `*export` file in the working directory, rewrites its paths, and launches the code_aster run |
| `fds6.7.4` | FDS 6.7.4 | Bash script that sources the FDS environment (`FDS6VARS.sh`), normalises input file names (`.FDS` → `.fds`), sets `ulimit`, and launches the FDS run |

Both scripts are released under GPLv3 (see headers).
