import asyncio
from typing import Any, AsyncGenerator
import httpx
from squinted_eye.lib.logger import logger
from squinted_eye.lib.result_logger import result_logger

logger = logger(name="discord_monitor")
result_logger = result_logger(name="discord_monitor_results")

async def check_discord_token(token: str) -> bool:
    """Check if the provided account token (that we will be using to monitor) is valid."""
    url = "https://discord.com/api/v9/users/@me"
    headers = {"Authorization": token}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                logger.info("Discord token is valid.")
                return True
            else:
                logger.error(f"Invalid Discord token. Status code: {response.status_code}")
                return False
        except httpx.RequestError as e:
            logger.error(f"Error while checking Discord token: {e}")
            return False

async def check_target_account(token: str, target_user_id: str) -> bool:
    """Check if the target account is valid and accessible with the provided token."""
    url = f"https://discord.com/api/v9/users/{target_user_id}/profile"
    headers = {"Authorization": token}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                logger.info(f"Target account {target_user_id} is valid")
                return True
            else:
                logger.error(f"Invalid target account. Status code: {response.status_code}")
                return False
        except httpx.RequestError as e:
            logger.error(f"Error while checking target account: {e}")
            return False

async def fetch_target_info(client: httpx.AsyncClient, token: str, target_user_id: str) -> dict[str, Any] | None:
    """Fetch the target account's information using the provided token and user ID."""
    url = f"https://discord.com/api/v9/users/{target_user_id}/profile"
    headers = {"Authorization": token}

    try:
        response = await client.get(url, headers=headers)
        
        # Basic Rate Limit (429) Handling to prevent bans
        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 5)
            logger.warning(f"Rate limited. Sleeping for {retry_after} seconds.")
            await asyncio.sleep(retry_after)
            return await fetch_target_info(client, token, target_user_id)
            
        if response.status_code != 200:
            logger.error(f"Failed to fetch target account info. Status code: {response.status_code}")
            return None
            
        # Ensure we don't crash if Discord returns HTML (like on a 502/504 error)
        if "application/json" in response.headers.get("content-type", ""):
            logger.debug(f"Response.json: {response.json()}")
            return response.json()
        else:
            logger.error("Received non-JSON response from Discord API.")
            return None
            
    except (httpx.RequestError, ValueError) as e:
        logger.error(f"Error while checking target account: {e}")
        return None

async def change_detector(token: str, target_user_id: str, interval: int) -> AsyncGenerator[dict[str, Any], None]:
    """Repeatedly fetch target account information and return detected changes."""
    
    previous_info = None

    def find_changes(old, new, path=""):
        changes = {}

        if isinstance(old, dict) and isinstance(new, dict):
            all_keys = old.keys() | new.keys()

            for key in all_keys:
                current_path = f"{path}.{key}" if path else str(key)

                if key not in old:
                    changes[current_path] = {"old": None, "new": new[key]}
                elif key not in new:
                    changes[current_path] = {"old": old[key], "new": None}
                else:
                    changes.update(find_changes(old[key], new[key], current_path))

        elif isinstance(old, list) and isinstance(new, list):
            # 1. Handle lists of Discord objects (like mutual_guilds)
            if (all(isinstance(x, dict) and 'id' in x for x in old) and 
                all(isinstance(x, dict) and 'id' in x for x in new)):
                
                # Transform lists into dictionaries keyed by their 'id'
                old_mapped = {x['id']: x for x in old}
                new_mapped = {x['id']: x for x in new}
                
                # Recursively pass back to the dictionary comparison logic above
                changes.update(find_changes(old_mapped, new_mapped, path))
            
            else:
                # 2. Handle simple lists (e.g., lists of strings or integers)
                try:
                    # Sort them first so order doesn't trigger false positives
                    old_list = sorted(old)
                    new_list = sorted(new)
                except TypeError:
                    # Fallback for un-sortable mixed types
                    old_list = old
                    new_list = new

                max_length = max(len(old_list), len(new_list))

                for i in range(max_length):
                    current_path = f"{path}[{i}]"

                    if i >= len(old_list):
                        changes[current_path] = {"old": None, "new": new_list[i]}
                    elif i >= len(new_list):
                        changes[current_path] = {"old": old_list[i], "new": None}
                    else:
                        changes.update(find_changes(old_list[i], new_list[i], current_path))

        elif old != new:
            changes[path] = {"old": old, "new": new}

        return changes

    # Use a single client for the loop to take advantage of connection pooling
    async with httpx.AsyncClient() as client:
        while True:
            current_info = await fetch_target_info(client, token, target_user_id)

            if not current_info:
                logger.error("Failed to fetch target account info. Skipping this iteration.")
                await asyncio.sleep(interval)
                continue

            if previous_info is not None:
                changes = find_changes(previous_info, current_info)

                if changes:
                    logger.info("Changes detected:")

                    for path, change in changes.items():
                        logger.info("%s: %r -> %r", path, change["old"], change["new"])

                    # Yield instead of return so the loop continues running
                    yield changes

            previous_info = current_info
            await asyncio.sleep(interval)

async def discord_monitor(token: str, user_id: str, interval: int = 60):
    logger.info("Starting Discord monitor...")
    
    if not await check_discord_token(token):
        logger.error("Invalid Discord token. Exiting Discord monitor.")
        return
    else:
        logger.debug("Discord token is valid. Proceeding.")
    
    if not await check_target_account(token, user_id):
        logger.error(f"Invalid target account ID: {user_id}. Exiting Discord monitor.")
        return
    else:
        logger.debug(f"Target account ID {user_id} is valid. Proceeding.")

    # Actually execute the monitor loop
    async for changes in change_detector(token, user_id, interval):
        result_logger.hit(f"Detected changes in target account {user_id}: {changes}")
        pass