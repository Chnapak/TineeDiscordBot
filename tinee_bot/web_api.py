from aiohttp import web

from . import settings
from . import state
from . import storage


def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PATCH,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization,Content-Type"
    return response


def is_request_authorized(request):
    if not settings.CONFIG_API_TOKEN:
        return True
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    if not token:
        token = request.query.get("token")
    return token == settings.CONFIG_API_TOKEN


def json_response(data, status=200):
    response = web.json_response(data, status=status)
    return add_cors_headers(response)


@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        response = web.Response(status=204)
        return add_cors_headers(response)
    response = await handler(request)
    return add_cors_headers(response)


@web.middleware
async def auth_middleware(request, handler):
    if request.method == "OPTIONS":
        return await handler(request)
    if not is_request_authorized(request):
        return json_response({"error": "unauthorized"}, status=401)
    return await handler(request)


async def start_config_api(bot):
    if not settings.CONFIG_API_ENABLED:
        return

    async def handle_health(request):
        return json_response({"status": "ok"})

    async def handle_guilds(request):
        guilds = [{"id": guild.id, "name": guild.name} for guild in bot.guilds]
        return json_response({"guilds": guilds})

    async def handle_guild_channels(request):
        guild_id = request.match_info.get("guild_id")
        try:
            guild_id = int(guild_id)
        except (TypeError, ValueError):
            return json_response({"error": "invalid guild id"}, status=400)
        guild = bot.get_guild(guild_id)
        if not guild:
            return json_response({"error": "guild not found"}, status=404)
        channels = [{"id": channel.id, "name": channel.name} for channel in guild.text_channels]
        return json_response({"channels": channels})

    async def handle_get_config(request):
        guild_id = request.match_info.get("guild_id")
        try:
            guild_id = int(guild_id)
        except (TypeError, ValueError):
            return json_response({"error": "invalid guild id"}, status=400)
        guild = bot.get_guild(guild_id)
        if not guild:
            return json_response({"error": "guild not found"}, status=404)
        config = storage.get_guild_config(guild_id)
        return json_response({"config": config})

    async def handle_update_config(request):
        guild_id = request.match_info.get("guild_id")
        try:
            guild_id = int(guild_id)
        except (TypeError, ValueError):
            return json_response({"error": "invalid guild id"}, status=400)
        guild = bot.get_guild(guild_id)
        if not guild:
            return json_response({"error": "guild not found"}, status=404)
        try:
            data = await request.json()
        except Exception:
            return json_response({"error": "invalid json"}, status=400)
        if not isinstance(data, dict):
            return json_response({"error": "invalid payload"}, status=400)

        config = storage.get_guild_config(guild_id)
        allowed_keys = {"ai_enabled", "ai_trigger", "ai_keyword", "ai_channels", "autoplay", "volume"}
        for key in allowed_keys:
            if key in data:
                config[key] = data[key]
        config = storage.normalize_guild_config(config)
        state.guild_configs[str(guild_id)] = config
        await storage.save_guild_configs()
        return json_response({"config": config})

    app = web.Application(middlewares=[cors_middleware, auth_middleware])
    app.add_routes([
        web.get("/health", handle_health),
        web.get("/guilds", handle_guilds),
        web.get("/guilds/{guild_id}/channels", handle_guild_channels),
        web.get("/config/{guild_id}", handle_get_config),
        web.patch("/config/{guild_id}", handle_update_config),
    ])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.CONFIG_API_HOST, settings.CONFIG_API_PORT)
    await site.start()
    state.config_api_runner = runner
    print(f"Config API running on http://{settings.CONFIG_API_HOST}:{settings.CONFIG_API_PORT}")
