![Docker Build](https://github.com/USERNAME/REPO/actions/workflows/docker.yml/badge.svg)
# Hitron CODA56 Prometheus Exporter

Prometheus exporter for the Hitron CODA56 DOCSIS 3.1 cable modem.

This exporter scrapes modem diagnostic endpoints directly from the modem web UI and exposes DOCSIS metrics for:

- Downstream channels
- Upstream channels
- OFDM downstream channels
- OFDMA upstream channels
- Signal levels
- SNR
- Frequency
- Corrected / uncorrectable codewords
- Scrape health

Designed for:
- Prometheus
- Grafana
- Alertmanager
- Docker / Kubernetes / HomeLab monitoring

---

# Features

- DOCSIS 3.1 telemetry
- OFDM + OFDMA support
- Prometheus-native metrics
- Docker-ready
- Multi-arch Docker builds
- GitHub Actions CI/CD
- Lightweight Flask exporter
- Handles broken modem TLS implementations

---

# Supported Modems

Tested with:

- Hitron CODA56

May also work with:
- CODA45
- CODA4582
- Other Hitron DOCSIS modems exposing `/data/*.asp` JSON endpoints

---

# Metrics

## Downstream

| Metric | Description |
|---|---|
| `modem_downstream_power_dbmv` | Downstream power |
| `modem_downstream_snr_db` | Downstream SNR |
| `modem_downstream_frequency_hz` | Downstream frequency |
| `modem_downstream_corrected_total` | Corrected codewords |
| `modem_downstream_uncorrectables_total` | Uncorrectable codewords |

## Upstream

| Metric | Description |
|---|---|
| `modem_upstream_power_dbmv` | Upstream transmit power |
| `modem_upstream_frequency_hz` | Upstream frequency |
| `modem_upstream_bandwidth_hz` | Upstream bandwidth |

## OFDM Downstream

| Metric | Description |
|---|---|
| `modem_ofdm_downstream_power_dbmv` | OFDM PLC power |
| `modem_ofdm_downstream_snr_db` | OFDM SNR |
| `modem_ofdm_downstream_frequency_hz` | OFDM frequency |

## OFDMA Upstream

| Metric | Description |
|---|---|
| `modem_ofdma_upstream_power_dbmv` | OFDMA upstream power |
| `modem_ofdma_upstream_frequency_hz` | OFDMA upstream frequency |
| `modem_ofdma_upstream_bandwidth_hz` | OFDMA upstream bandwidth |

## Exporter Health

| Metric | Description |
|---|---|
| `modem_scrape_success` | Whether scraping succeeded |

---

# Example Metrics

```text
modem_downstream_power_dbmv{channel="1"} 9.7
modem_downstream_snr_db{channel="1"} 40.9
modem_upstream_power_dbmv{channel="1"} 42.2
modem_ofdm_downstream_snr_db{channel="0"} 42
```

---

# Running with Docker

## docker-compose.yml

```yaml
services:

  modem-exporter:

    image: ghcr.io/YOUR_USERNAME/modem-exporter:latest

    container_name: modem-exporter

    restart: unless-stopped

    ports:
      - "9877:9877"

    environment:
      MODEM_URL: https://192.168.100.1
      VERIFY_SSL: "false"
```

Start:

```bash
docker compose up -d
```

---

# Local Development

## Requirements

- Python 3.11+

Install dependencies:

```bash
pip install -r requirements.txt
```

Run exporter:

```bash
python exporter.py
```

Exporter endpoint:

```text
http://localhost:9877/metrics
```

---

# Configuration

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MODEM_URL` | `https://192.168.100.1` | Modem base URL |
| `VERIFY_SSL` | `false` | Verify modem TLS certificate |
| `PORT` | `9877` | Exporter listen port |

---

# Prometheus Configuration

```yaml
scrape_configs:

  - job_name: modem

    scrape_interval: 30s

    static_configs:
      - targets:
          - modem-exporter:9877
```

---

# Grafana

Recommended dashboards:
- Downstream power per channel
- SNR per channel
- OFDM health
- Upstream power
- Corrected vs uncorrectables rate
- Scrape health

Useful PromQL:

```promql
avg(modem_downstream_snr_db)
```

```promql
rate(modem_downstream_uncorrectables_total[5m])
```

```promql
max(modem_upstream_power_dbmv)
```

---

# Alerting Examples

## Low SNR

```yaml
- alert: LowDownstreamSNR
  expr: modem_downstream_snr_db < 35
  for: 5m
```

## High Upstream Power

```yaml
- alert: HighUpstreamPower
  expr: modem_upstream_power_dbmv > 50
  for: 5m
```

## Exporter Failure

```yaml
- alert: ModemScrapeFailed
  expr: modem_scrape_success == 0
  for: 2m
```

---

# GitHub Actions

Included workflow:
- Multi-arch Docker builds
- GitHub Container Registry publishing
- Automatic tagging

Image location:

```text
ghcr.io/<username>/modem-exporter
```

---

# Troubleshooting

## TLS / SSL Problems

Some cable modems have broken HTTPS implementations.

Recommended:

```yaml
VERIFY_SSL: "false"
```

The exporter already handles:
- Broken TLS EOF behavior
- Connection reuse issues
- Embedded modem HTTPS quirks

---

## Empty Metrics

If metrics exist but values are missing:

- Verify modem accessibility
- Check Docker networking
- Test endpoint manually:

```bash
curl -k https://192.168.100.1/data/dsinfo.asp
```

---

# Known Endpoints

The exporter uses:

```text
/data/dsinfo.asp
/data/usinfo.asp
/data/dsofdminfo.asp
/data/usofdminfo.asp
```

---

# License

MIT License

---

# Disclaimer

This project is unofficial and not affiliated with Hitron Technologies.