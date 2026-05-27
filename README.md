# OpenVPNMesh

A self-hosted, containerized mesh VPN platform running across multiple nodes.

## Project Status

This repository contains the implementation of Phase 1 of the MeshVPN project as described in meshvpn-build-plan.md:

- Repository structure created
- docker-compose.yml defined with all services
- mesh.yaml.example template created
- Core service with config parsing implemented
- Database schema defined
- API endpoints stubbed
- Templates for configuration generation created
- Dockerfiles for all services created

## Services

- **core**: FastAPI mesh daemon with SQLite database
- **wg-manager**: WireGuard configuration manager
- **router**: IP route table manager
- **openvpn**: OpenVPN server
- **haproxy**: TCP frontend for OpenVPN
- **cloudflare**: DNS updater
- **frontend**: React web interface

## Getting Started

1. Copy `.env.example` to `.env` and set your configuration
2. Copy `mesh.yaml.example` to `mesh.yaml` and configure for your node
3. Run `docker compose up` to start all services

## Next Steps

Proceed to Phase 2: Leader mode implementation