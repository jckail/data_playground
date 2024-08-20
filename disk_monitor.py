import psutil
import time
from prometheus_client import start_http_server, Gauge

disk_usage = Gauge('disk_usage_percent', 'Disk usage in percent')

def monitor_disk():
    while True:
        usage = psutil.disk_usage('/').percent
        disk_usage.set(usage)
        if usage > 80:
            print(f"WARNING: Disk usage is at {usage}%")
        time.sleep(60)

if __name__ == '__main__':
    start_http_server(8000)
    monitor_disk()