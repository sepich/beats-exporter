# beats-exporter

Prometheus format exporter for Elastic Beats internal stats.  
Alternative implementation of [trustpilot/beat-exporter](https://github.com/trustpilot/beat-exporter) supporting:  
 - Exposing multiple Beats from single instance
 - Filter metrics to expose

## Kubernetes example
Example deployment for Kubernetes provided in `kubernetes-example.yml`. It is DaemonSet with 3 containers in each pod to be scheduled to each k8s cluster node. `Filebeat` reads docker container logs (stdout/stderr), `Journalbeat` reads systemd-journal and `beats-exporter` exports stats for both previous containers.

Here are some highlights:  
Enable Beats internal metrics exposure in config:
```yml
    # Stats can be access through http://localhost:5066/stats
    http:
      enabled: true
      port: 5066
```
As both `Filebeat` and `Journalbeat` use the same configmap with `port: 5066` we override `Journalbeat` to use another port:
```yml
      - name: journalbeat
        image: docker.elastic.co/beats/journalbeat:7.4.0
        args:
          - -c
          - /etc/beats/beats.yml
          - -e
          - -E
          - http.port=5067
```
Next, we configure `beats-exporter` to collect metrics from these two ports:
```yml
      - name: exporter
        image: sepa/beats-exporter
        args:
          - -p=5066
          - -p=5067
```
And configure automatic Prometheus discovery:
```yml
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
```
You should start to receive metrics in Prometheus:
```bash
$ k -n kube-system exec beats-9chbm -- curl -s localhost:8080/metrics | grep info
Defaulting container name to filebeat.
Use 'kubectl describe pod/beats-9chbm -n kube-system' to see all of the containers in this pod.
filebeat_info{version="7.4.0"} 1
filebeat_beat_info_uptime_ms 5268342
journalbeat_info{version="7.4.0"} 1
journalbeat_beat_info_uptime_ms 5268038
```
Example Alert:
```yml
  - alert: FileBeatQueue
    expr: filebeat_libbeat_pipeline{events="active"} >100 and delta(filebeat_libbeat_pipeline{events="active"}[15m]) >0
    for: 15m
    labels:
      severity: warning
      instance: '{{$labels.kubernetes_pod_node_name}}'
    annotations:
      description: Filebeat queue is {{printf "%.0f" $value}} and growing
```

### Kubernetes example for exposed metric with non-default port
if `beats-exporter` exposes  on non-default port 8088:
```yml
      - name: exporter
        image: sepa/beats-exporter
        args:
          - -l=info
          - -p=5066
          - -m=8088
```
configure automatic Prometheus discovery on correct port.
```yml
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8088"

```

## Usage
```
$ docker run sepa/beats-exporter -h
usage: beats-exporter [-h] [-p PORT] [-f FILTER] [-l {info,warn,error}]
                      [-m METRICS_PORT]

Prometheus exporter for Elastic Beats

optional arguments:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  Port to scrape (default: 5066)
  -f FILTER, --filter FILTER
                        Filter metrics (default: disabled)
  -l {info,warn,error}, --log {info,warn,error}
                        Logging level (default: info)
  -m METRICS_PORT, --metrics-port METRICS_PORT
                        Expose metrics on port (default: 8080)
```
You can use multiple `port` arguments to scrape multiple Beats from same instance of exporter.

To reduce number of metrics (cardinality) you can use (multiple) `filter` arguments. Filter return only metrics matched to substring you've set. For example:
```
$ ./beats-exporter.py -f=error -f=version
$ curl localhost:8080/metrics
filebeat_info{version="7.4.0"} 1
filebeat_libbeat_output{read="errors"} 0
filebeat_libbeat_output{write="errors"} 0
```