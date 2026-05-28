import json
import os
import threading
import time
import urllib3
import requests

from flask import Flask, Response
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
from requests.adapters import HTTPAdapter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG = {
    "modem_url": os.getenv("MODEM_URL", "https://192.168.100.1"),
    "verify_ssl": os.getenv("VERIFY_SSL", "false").lower() == "true",
    "port": int(os.getenv("PORT", "9877")),
    "scrape_interval": int(os.getenv("SCRAPE_INTERVAL", "30"))
}

app = Flask(__name__)

#
# Requests session
#
session = requests.Session()

adapter = HTTPAdapter(
    pool_connections=1,
    pool_maxsize=1,
    max_retries=0
)

session.mount("https://", adapter)

session.headers.update({
    "Connection": "close",
    "User-Agent": "Mozilla/5.0"
})

#
# Global state
#
last_scrape = 0
scrape_lock = threading.Lock()

#
# Metrics
#

SCRAPE_SUCCESS = Gauge(
    "modem_scrape_success",
    "Whether modem scrape succeeded"
)

SCRAPE_AGE = Gauge(
    "modem_scrape_age_seconds",
    "Age of last successful scrape"
)

#
# Downstream
#
DOWNSTREAM_POWER = Gauge(
    "modem_downstream_power_dbmv",
    "DOCSIS downstream power",
    ["channel"]
)

DOWNSTREAM_SNR = Gauge(
    "modem_downstream_snr_db",
    "DOCSIS downstream SNR",
    ["channel"]
)

DOWNSTREAM_FREQ = Gauge(
    "modem_downstream_frequency_hz",
    "DOCSIS downstream frequency",
    ["channel"]
)

DOWNSTREAM_CORRECTED = Gauge(
    "modem_downstream_corrected_total",
    "DOCSIS corrected codewords",
    ["channel"]
)

DOWNSTREAM_UNCORRECTABLE = Gauge(
    "modem_downstream_uncorrectables_total",
    "DOCSIS uncorrectable codewords",
    ["channel"]
)

#
# Upstream
#
UPSTREAM_POWER = Gauge(
    "modem_upstream_power_dbmv",
    "DOCSIS upstream transmit power",
    ["channel"]
)

UPSTREAM_FREQ = Gauge(
    "modem_upstream_frequency_hz",
    "DOCSIS upstream frequency",
    ["channel"]
)

UPSTREAM_BW = Gauge(
    "modem_upstream_bandwidth_hz",
    "DOCSIS upstream bandwidth",
    ["channel"]
)

#
# OFDM Downstream
#
OFDM_POWER = Gauge(
    "modem_ofdm_downstream_power_dbmv",
    "DOCSIS OFDM downstream PLC power",
    ["channel"]
)

OFDM_SNR = Gauge(
    "modem_ofdm_downstream_snr_db",
    "DOCSIS OFDM downstream SNR",
    ["channel"]
)

OFDM_FREQ = Gauge(
    "modem_ofdm_downstream_frequency_hz",
    "DOCSIS OFDM downstream frequency",
    ["channel"]
)

#
# OFDMA Upstream
#
OFDMA_POWER = Gauge(
    "modem_ofdma_upstream_power_dbmv",
    "DOCSIS OFDMA upstream power",
    ["channel"]
)

OFDMA_FREQ = Gauge(
    "modem_ofdma_upstream_frequency_hz",
    "DOCSIS OFDMA upstream frequency",
    ["channel"]
)

OFDMA_BW = Gauge(
    "modem_ofdma_upstream_bandwidth_hz",
    "DOCSIS OFDMA upstream bandwidth",
    ["channel"]
)


def fetch_json(endpoint):

    url = f"{CONFIG['modem_url']}/data/{endpoint}"

    print(f"Fetching {url}")

    r = session.get(
        url,
        timeout=20,
        verify=CONFIG["verify_ssl"],
        allow_redirects=True,
        stream=False
    )

    r.raise_for_status()

    body = r.content.decode(
        "utf-8",
        errors="ignore"
    )

    return json.loads(body)


def safe_float(value):

    try:
        return float(str(value).strip())
    except Exception:
        return 0.0


def scrape_modem():

    #
    # Downstream SC-QAM
    #
    ds = fetch_json("dsinfo.asp")

    for ch in ds:

        channel = ch.get("channelId", ch.get("portId"))

        DOWNSTREAM_POWER.labels(
            channel=channel
        ).set(
            safe_float(ch.get("signalStrength"))
        )

        DOWNSTREAM_SNR.labels(
            channel=channel
        ).set(
            safe_float(ch.get("snr"))
        )

        DOWNSTREAM_FREQ.labels(
            channel=channel
        ).set(
            safe_float(ch.get("frequency"))
        )

        DOWNSTREAM_CORRECTED.labels(
            channel=channel
        ).set(
            safe_float(ch.get("correcteds"))
        )

        DOWNSTREAM_UNCORRECTABLE.labels(
            channel=channel
        ).set(
            safe_float(ch.get("uncorrect"))
        )

    #
    # Upstream SC-QAM
    #
    us = fetch_json("usinfo.asp")

    for ch in us:

        channel = ch.get("channelId", ch.get("portId"))

        UPSTREAM_POWER.labels(
            channel=channel
        ).set(
            safe_float(ch.get("signalStrength"))
        )

        UPSTREAM_FREQ.labels(
            channel=channel
        ).set(
            safe_float(ch.get("frequency"))
        )

        UPSTREAM_BW.labels(
            channel=channel
        ).set(
            safe_float(ch.get("bandwidth"))
        )

    #
    # OFDM Downstream
    #
    dsofdm = fetch_json("dsofdminfo.asp")

    for idx, ch in enumerate(dsofdm):

        channel = str(idx)

        OFDM_POWER.labels(
            channel=channel
        ).set(
            safe_float(ch.get("plcpower"))
        )

        OFDM_SNR.labels(
            channel=channel
        ).set(
            safe_float(ch.get("SNR"))
        )

        OFDM_FREQ.labels(
            channel=channel
        ).set(
            safe_float(ch.get("Subcarr0freqFreq"))
        )

        DOWNSTREAM_CORRECTED.labels(
            channel=f"ofdm_{channel}"
        ).set(
            safe_float(ch.get("correcteds"))
        )

        DOWNSTREAM_UNCORRECTABLE.labels(
            channel=f"ofdm_{channel}"
        ).set(
            safe_float(ch.get("uncorrect"))
        )

    #
    # OFDMA Upstream
    #
    usofdm = fetch_json("usofdminfo.asp")

    for ch in usofdm:

        state = str(ch.get("state", "")).strip()

        if state != "OPERATE":
            continue

        channel = str(ch.get("uschindex"))

        OFDMA_POWER.labels(
            channel=channel
        ).set(
            safe_float(ch.get("repPower1_6"))
        )

        OFDMA_FREQ.labels(
            channel=channel
        ).set(
            safe_float(ch.get("frequency"))
        )

        #
        # MHz -> Hz
        #
        OFDMA_BW.labels(
            channel=channel
        ).set(
            safe_float(ch.get("channelBw")) * 1000000
        )

    SCRAPE_SUCCESS.set(1)


def scrape_loop():

    global last_scrape

    while True:

        try:

            with scrape_lock:

                scrape_modem()

                last_scrape = time.time()

                SCRAPE_AGE.set(0)

                print("Modem scrape successful")

        except Exception as e:

            SCRAPE_SUCCESS.set(0)

            print(f"Scrape failed: {e}")

        time.sleep(CONFIG["scrape_interval"])


@app.route("/metrics")
def metrics():

    if last_scrape > 0:

        SCRAPE_AGE.set(
            time.time() - last_scrape
        )

    return Response(
        generate_latest(),
        mimetype=CONTENT_TYPE_LATEST
    )


@app.route("/")
def index():

    return {
        "status": "ok",
        "metrics": "/metrics"
    }


if __name__ == "__main__":

    t = threading.Thread(
        target=scrape_loop,
        daemon=True
    )

    t.start()

    app.run(
        host="0.0.0.0",
        port=CONFIG["port"]
    )