import os
import time
import logging
import requests

URL = os.environ.get("INVENTORY_URL", "http://inventory:8080/inventory/apple")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

while True:
    try:
        # new connection every time so requests can go to different pods
        r = requests.get(URL, timeout=2, headers={"Connection": "close"})
        data = r.json()
        logging.info("status=%s item=%s stock=%s pod=%s",
                     r.status_code, data.get("item"), data.get("stock"), data.get("pod"))
    except Exception as e:
        logging.info("ERROR %s", e)
    time.sleep(1)
