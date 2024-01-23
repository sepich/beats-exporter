#!/usr/bin/env python
import argparse
import aiohttp
import aiohttp.web
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("beats-exporter")


class ExporterException(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        prog="beats-exporter", description="Prometheus exporter for Elastic Beats"
    )
    parser.add_argument(
        "-p",
        "--port",
        action="append",
        type=int,
        default=[5066],
        help="Port to scrape (default: 5066)",
    )
    parser.add_argument(
        "-f",
        "--filter",
        action="append",
        type=str,
        default=[],
        help="Filter metrics (default: disabled)",
    )
    parser.add_argument(
        "-l",
        "--log",
        choices=["info", "warn", "error"],
        default="info",
        help="Logging level (default: info)",
    )
    parser.add_argument(
        "-m",
        "--metrics-port",
        action="store",
        type=int,
        default=8080,
        help="Expose metrics on port (default: 8080)",
    )
    args = parser.parse_args()
    logger.setLevel(getattr(logging, args.log.upper()))
    return args


async def handler(request):
    text = []
    async with aiohttp.ClientSession() as session:
        for port in set(request.app["args"].port):
            try:
                async with session.get(f"http://localhost:{port}/stats") as r:
                    data = await r.json()
                prefix, version = get_info(data)
                text.append(f'{prefix}_info{{version="{version}"}} 1')
                text.extend(get_metric(data, prefix))
            except aiohttp.client_exceptions.ClientConnectorError as e:
                logger.error(f"Error reading from port {port}: {e}")
                return aiohttp.web.Response(status=500, text=str(e))
            except ExporterException as e:
                logger.error(f"Invalid response from {port}: {e}")

    if request.app["args"].filter:
        tmp = text
        text = []
        for line in tmp:
            for sub in set(request.app["args"].filter):
                if sub in line:
                    text.append(line)
                    break

    return aiohttp.web.Response(text="\n".join(text))


def get_info(data):
    if "beat" not in data:
        raise ExporterException("invalid response, beat key not found")

    if "info" not in data["beat"]:
        raise ExporterException("invalid response, info key not found")

    if "name" not in data["beat"]["info"]:
        raise ExporterException("invalid response, name key not found")

    if "version" not in data["beat"]["info"]:
        raise ExporterException("invalid response, version key not found")

    return data["beat"]["info"]["name"], data["beat"]["info"]["version"]


def get_metric(data, prefix):
    result = []
    for k, v in data.items():
        if type(v) is dict:
            if not [x for x in v if type(v[x]) in [dict, str]] and len(v) > 1:
                result += [f'{prefix}{{{k}="{x}"}} {v[x]}' for x in v]
            else:
                result += get_metric(v, f"{prefix}_{k}")
        elif type(v) is str:
            result += [f'{prefix}{{{k}="{v}"}} 1']
        else:
            result += [f"{prefix}_{k} {v}"]
    return result


if __name__ == "__main__":
    args = parse_args()
    loop = asyncio.get_event_loop()

    app = aiohttp.web.Application()
    app.router.add_get("/metrics", handler)
    app["args"] = args
    aiohttp.web.run_app(app, port=args.metrics_port, access_log=logger)
