#!/usr/bin/env python
import argparse
import asyncio
import aiohttp
from aiohttp import web
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(prog='beats-exporter', description='Prometheus exporter for Elastic Beats')
    parser.add_argument('-p', '--port', action='append', type=int, default=[5066], help='Port to scrape (default: 5066)')
    parser.add_argument('-f', '--filter', action='append', type=str, default=[], help='Filter metrics (default: disabled)')
    parser.add_argument('-l', '--log', choices=['info', 'warn', 'error'], default='info', help='Logging level (default: info)')
    args = parser.parse_args()
    logger.setLevel(getattr(logging, args.log.upper()))
    return args


async def handler(request):
    text = []
    async with aiohttp.ClientSession() as session:
        for port in set(request.app['args'].port):
            try:
                name = request.app['beats'][port]['beat']
                text += [f'{name}_info{{version="{request.app["beats"][port]["version"]}"}} 1']
                async with session.get(f'http://localhost:{port}/stats') as r:
                    data = await r.json()
                text += get_metric(data=data, prefix=name)
            except Exception as e:
                logger.error(f"Error reading {request.app['beats'][port]['beat']} at port {port}:\n{e}")
                return web.Response(status=500, text=str(e))

    if request.app['args'].filter:
        tmp = text
        text = []
        for line in tmp:
            for sub in set(request.app['args'].filter):
                if sub in line:
                    text.append(line)
                    break

    return web.Response(text='\n'.join(text))


async def get_info(args):
    beats = {}
    async with aiohttp.ClientSession() as session:
        for port in set(args.port):
            try:
                async with session.get(f'http://localhost:{port}') as r:
                    beats[port] = await r.json()
            except Exception as e:
                logger.error(f"Error connecting Beat at port {port}:\n{e}")
                sys.exit(1)
    return beats


def get_metric(data, prefix):
    text = []
    for k in data:
        if type(data[k]) == dict:
            text += get_metric(data[k], f'{prefix}_{k}')
        elif type(data[k]) == str:
            text += [f'{prefix}{{{k}="{data[k]}"}} 1']
        else:
            text += [f'{prefix}_{k} {data[k]}']
    return text


if __name__ == "__main__":
    args = parse_args()
    loop = asyncio.get_event_loop()

    app = web.Application()
    app.router.add_get("/metrics", handler)
    app['args'] = args
    app['beats'] = loop.run_until_complete(get_info(args))
    web.run_app(app, access_log=logger)
