from odc.monitoring.metrics import get_metrics_collector

# Get metrics in Prometheus format
metrics = get_metrics_collector()
prometheus_text = metrics.get_metrics_text()
print(prometheus_text)




# import fastapi
# from odc.monitoring.metrics import get_metrics_collector

# app = fastapi.FastAPI(title='Odata Metrics')

# @app.get('/metrics')
# def metrics():
#     collector = get_metrics_collector()
#     return collector.get_metrics_text(), 200, {'Content-Type': 'text/plain'}