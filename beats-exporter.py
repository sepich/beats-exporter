#!/usr/bin/env python3
import asyncio
from aiohttp import web


async def handle(request):
    name = request.match_info.get('name', '?')
    if name == 'sleep':
        await asyncio.sleep(10)
    return web.Response(text=f'Hello, {name}')

app = web.Application()
app.add_routes([
    web.get('/', handle),
    web.get('/{name}', handle),
])

web.run_app(app)
