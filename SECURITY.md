# Security Policy

CFD FEA SERVICE S.R.L. takes the security of the cloudHPC platform (https://cloudhpc.cloud) and of its public repositories seriously. We welcome responsible reports of vulnerabilities from researchers, customers and the community.

## Reporting a vulnerability

Please report security issues by email to **support@cloudhpc.cloud**.

Do **not** open a public GitHub issue, pull request or discussion for a security problem.

To help us triage quickly, please include:

- a description of the issue and its potential impact;
- the affected URL, component or file;
- step-by-step instructions or a proof of concept to reproduce it;
- any relevant logs or screenshots (without real customer data);
- your name or handle if you would like to be credited.

## What to expect

- **Acknowledgement:** within 3 business days of your report.
- **Assessment:** we will confirm whether the report is valid and share an initial severity evaluation within 10 business days.
- **Resolution:** we will keep you informed of progress and notify you when the issue is fixed. Fix times depend on severity and complexity.
- **Credit:** with your consent, we are happy to acknowledge your contribution once the issue is resolved.

## Scope

In scope:

- the cloudHPC web application and API (https://cloudhpc.cloud);
- the code in this repository.

Out of scope:

- denial-of-service or volumetric attacks, and automated scanning that generates heavy traffic;
- social engineering, phishing or physical attacks against staff or customers;
- vulnerabilities in third-party services we use (report them to the respective vendor);
- findings without a demonstrable security impact (e.g. missing best-practice headers with no exploit path, or software version banners).

## Rules of engagement

To keep customers and their data safe, please:

- test only against your own accounts and data;
- do not access, modify or delete data belonging to other users, and stop and report as soon as you gain access to data that is not yours;
- do not disrupt the service or degrade it for other users;
- give us reasonable time to fix the issue before any public disclosure.

If you act in good faith and follow this policy, we will not pursue legal action against you for your research.

## Supported versions

Security fixes are applied to the version of cloudHPC currently running in production and to the latest state of the main branch of this repository.
