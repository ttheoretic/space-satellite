"""Testumgebung: eigene temporäre Datenbank, kein Internetzugriff."""

import os
import tempfile

# Muss gesetzt sein, bevor app.config importiert wird
os.environ["ORBITDESK_DATA_DIR"] = tempfile.mkdtemp(prefix="orbitdesk-test-")
os.environ["ORBITDESK_TLE_ONLINE"] = "false"
os.environ["ORBITDESK_BACKFILL_HOURS"] = "0.5"
