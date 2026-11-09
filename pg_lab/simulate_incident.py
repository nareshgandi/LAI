"""Creates a realistic lock incident in bankdb and keeps it alive.

Blocking tree, as pg_blocking_pids() reports it:

    payments-batch   (idle in transaction, holds row id=1)       <- ROOT BLOCKER, blocks 1
      +-- payments-api-1  (holds row id=2, first in queue for id=1) <- blocked AND blocks 2
            +-- payments-api-2  (queued behind payments-api-1 for id=1)
            +-- reports-job     (waits for id=2)

The trap: payments-api-1 blocks the MOST sessions, but it is a victim, not the cause.

Run it in its own terminal and leave it running:  python simulate_incident.py
Stop with Ctrl+C.
"""
import os
import threading
import time

import psycopg
from dotenv import load_dotenv

load_dotenv()
DSN = os.environ["APP_DSN"]
stop = threading.Event()


def session(app_name, statements, hold=False):
    try:
        with psycopg.connect(DSN, application_name=app_name) as conn:   # autocommit off = one transaction
            for sql in statements:
                conn.execute(sql)
            if hold:
                print(f"[{app_name}] pid {conn.info.backend_pid}: got its lock, now idle in transaction")
                while not stop.is_set():
                    time.sleep(1)
                conn.rollback()
            else:
                conn.commit()
                print(f"[{app_name}] finished: lock was released")
    except psycopg.OperationalError as exc:
        print(f"[{app_name}] connection ended: {str(exc).strip()[:80]}")


def start(app_name, statements, hold=False):
    t = threading.Thread(target=session, args=(app_name, statements, hold), daemon=True)
    t.start()
    time.sleep(1)  # keep the order deterministic


if __name__ == "__main__":
    start("payments-batch", ["UPDATE accounts SET balance = balance - 500 WHERE id = 1"], hold=True)
    start("payments-api-1", ["UPDATE accounts SET balance = balance + 10 WHERE id = 2",
                             "UPDATE accounts SET balance = balance + 10 WHERE id = 1"])
    start("payments-api-2", ["UPDATE accounts SET balance = balance + 20 WHERE id = 1"])
    start("reports-job",    ["UPDATE accounts SET balance = balance WHERE id = 2"])
    print("\nIncident running. Leave this terminal open; run the labs in another one. Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop.set()
        time.sleep(1.5)
        print("Simulator stopped.")
