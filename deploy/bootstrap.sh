#!/usr/bin/env bash
set -euo pipefail
dnf update -y
dnf install -y python3.11 python3.11-pip nginx git
id smartflow >/dev/null 2>&1 || useradd --system --create-home smartflow
mkdir -p /opt/smartflow
chown -R smartflow:smartflow /opt/smartflow
echo "Clone the application into /opt/smartflow, install requirements, and copy .env before enabling services."
