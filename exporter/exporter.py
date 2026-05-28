import os
import json
import argparse
import traceback
import requests
import urllib3

from flask import Flask, Response
from prometheus_client import Gauge, generate_latest

#
# Disable warnings for self-signed modem certificates
#

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

DEFAULT_MODEM_URL = "https://192.168.100.1"
CONFIG_FILE = "config.json"

#
# Configuration loader
#

def load_config():

    config = {}

    #
    # Config file
    #
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Failed to load config file: {e}")

    #
    # Environment variables
    #
    env_url = os.getenv("MODEM_URL")
    env_verify_ssl = os.getenv("VERIFY_SSL", "false")

    #
    # CLI args
    #
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--modem-url",
        help="Modem base URL"
    )

    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        help="Enable SSL verification"
    )

    args, _ = parser.parse_known_args()

    modem_url = (
        args.modem_url
        or env_url
        or config.get("modem_url")
        or DEFAULT_MODEM_URL
    )

    verify_ssl = (
        args.verify_ssl
        or env_verify_ssl.lower() == "true"
        or config.get("verify_ssl", False)
    )

    return {
        "modem_url": modem_url.rstrip("/"),
        "verify_ssl": verify_ssl
    }


CONFIG = load_config()

print("======================================")
print(f"MODEM URL : {CONFIG['modem_url']}")
print(f"VERIFY SSL: {CONFIG['verify_ssl']}")
print("======================================")

#
# Helpers
#

def safe_float(value, default=0):

    try:

        if value is None:
            return default

        value = str(value).strip()

        if value == "":
            return default

        if value in ["--", "nan", "NaN", "N/A"]:
            return default

        return float(value)

    except Exception:
        return default


def fetch_json(endpoint):

    url = f"{CONFIG['modem_url']}/data/{endpoint}"

    print(f"Fetching: {url}")

    r = requests.get(
        url,
        timeout=15,
        verify=CONFIG["verify_ssl"],
        allow_redirects=True
    )

    r.raise_for_status()

    try:
        return r.json()

    except Exception:

        print("======================================")
        print("INVALID JSON RESPONSE")
        print("======================================")
        print(r.text[:2000])

        raise

#
# Prometheus metrics
#

scrape_success = Gauge(
    "modem_scrape_success",
    "Whether modem scrape succeeded"
)

#
# Downstream SC-QAM
#

downstream_power = Gauge(
    "modem_downstream_power_dbmv",
    "DOCSIS downstream power",
    ["channel"]
)

downstream_snr = Gauge(
    "modem_downstream_snr_db",
    "DOCSIS downstream SNR",
    ["channel"]
)

downstream_corrected = Gauge(
    "modem_downstream_corrected_total",
    "DOCSIS corrected codewords",
    ["channel"]
)

downstream_uncorrectables = Gauge(
    "modem_downstream_uncorrectables_total",
    "DOCSIS uncorrectable codewords",
    ["channel"]
)

downstream_frequency = Gauge(
    "modem_downstream_frequency_hz",
    "DOCSIS downstream frequency",
    ["channel"]
)

#
# Upstream SC-QAM
#

upstream_power = Gauge(
    "modem_upstream_power_dbmv",
    "DOCSIS upstream transmit power",
    ["channel"]
)

upstream_frequency = Gauge(
    "modem_upstream_frequency_hz",
    "DOCSIS upstream frequency",
    ["channel"]
)

upstream_bandwidth = Gauge(
    "modem_upstream_bandwidth_hz",
    "DOCSIS upstream bandwidth",
    ["channel"]
)

#
# OFDM Downstream
#

ofdm_downstream_power = Gauge(
    "modem_ofdm_downstream_power_dbmv",
    "DOCSIS OFDM downstream PLC power",
    ["channel"]
)

ofdm_downstream_snr = Gauge(
    "modem_ofdm_downstream_snr_db",
    "DOCSIS OFDM downstream SNR",
    ["channel"]
)

ofdm_downstream_frequency = Gauge(
    "modem_ofdm_downstream_frequency_hz",
    "DOCSIS OFDM downstream frequency",
    ["channel"]
)

#
# OFDMA Upstream
#

ofdma_upstream_power = Gauge(
    "modem_ofdma_upstream_power_dbmv",
    "DOCSIS OFDMA upstream power",
    ["channel"]
)

ofdma_upstream_frequency = Gauge(
    "modem_ofdma_upstream_frequency_hz",
    "DOCSIS OFDMA upstream frequency",
    ["channel"]
)

ofdma_upstream_bandwidth = Gauge(
    "modem_ofdma_upstream_bandwidth_hz",
    "DOCSIS OFDMA upstream bandwidth",
    ["channel"]
)

#
# Main scrape function
#

def scrape_modem():

    try:

        #
        # Downstream SC-QAM
        #
        try:

            dsinfo = fetch_json("dsinfo.asp")

            for ch in dsinfo:

                channel = str(ch.get("channelId", "0"))

                downstream_power.labels(
                    channel=channel
                ).set(safe_float(ch.get("signalStrength")))

                downstream_snr.labels(
                    channel=channel
                ).set(safe_float(ch.get("snr")))

                downstream_corrected.labels(
                    channel=channel
                ).set(safe_float(ch.get("correcteds")))

                downstream_uncorrectables.labels(
                    channel=channel
                ).set(safe_float(ch.get("uncorrect")))

                downstream_frequency.labels(
                    channel=channel
                ).set(safe_float(ch.get("frequency")))

        except Exception:
            print("Downstream scrape failed")
            traceback.print_exc()

        #
        # Upstream SC-QAM
        #
        try:

            usinfo = fetch_json("usinfo.asp")

            for ch in usinfo:

                channel = str(ch.get("channelId", "0"))

                upstream_power.labels(
                    channel=channel
                ).set(safe_float(ch.get("signalStrength")))

                upstream_frequency.labels(
                    channel=channel
                ).set(safe_float(ch.get("frequency")))

                upstream_bandwidth.labels(
                    channel=channel
                ).set(safe_float(ch.get("bandwidth")))

        except Exception:
            print("Upstream scrape failed")
            traceback.print_exc()

        #
        # OFDM Downstream
        #
        try:

            dsofdm = fetch_json("dsofdminfo.asp")

            for idx, ch in enumerate(dsofdm):

                channel = str(idx)

                ofdm_downstream_power.labels(
                    channel=channel
                ).set(safe_float(ch.get("plcpower")))

                ofdm_downstream_snr.labels(
                    channel=channel
                ).set(safe_float(ch.get("SNR")))

                freq = ch.get("Subcarr0freqFreq")

                if freq is not None:
                    ofdm_downstream_frequency.labels(
                        channel=channel
                    ).set(safe_float(str(freq).strip()))

                downstream_corrected.labels(
                    channel=f"ofdm_{channel}"
                ).set(safe_float(ch.get("correcteds")))

                downstream_uncorrectables.labels(
                    channel=f"ofdm_{channel}"
                ).set(safe_float(ch.get("uncorrect")))

        except Exception:
            print("OFDM downstream scrape failed")
            traceback.print_exc()

        #
        # OFDMA Upstream
        #
        try:

            usofdm = fetch_json("usofdminfo.asp")

            for ch in usofdm:

                channel = str(ch.get("uschindex", "0"))

                state = str(
                    ch.get("state", "")
                ).strip()

                #
                # Skip disabled channels
                #
                if state != "OPERATE":
                    continue

                ofdma_upstream_frequency.labels(
                    channel=channel
                ).set(safe_float(ch.get("frequency")))

                #
                # MHz -> Hz
                #
                bandwidth = safe_float(
                    ch.get("channelBw")
                ) * 1_000_000

                ofdma_upstream_bandwidth.labels(
                    channel=channel
                ).set(bandwidth)

                #
                # repPower1_6 is usually the realistic value
                #
                ofdma_upstream_power.labels(
                    channel=channel
                ).set(safe_float(ch.get("repPower1_6")))

        except Exception:
            print("OFDMA upstream scrape failed")
            traceback.print_exc()

        scrape_success.set(1)

    except Exception:

        print("======================================")
        print("SCRAPE FAILED")
        print("======================================")

        traceback.print_exc()

        scrape_success.set(0)

#
# Flask routes
#

@app.route("/")
def home():
    return "DOCSIS modem exporter OK"


@app.route("/metrics")
def metrics():

    scrape_modem()

    return Response(
        generate_latest(),
        mimetype="text/plain"
    )

#
# Main
#

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=9877
    )