from lib.logger import logger
import requests
logger = logger(name="discord_monitor")

def check_discord_token(token: str) -> bool:
    """Check if the provided account token (that we will be using to monitor) is valid."""

    url = "https://discord.com/api/v9/users/@me"
    headers = {"Authorization": token}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            logger.info("Discord token is valid.")
            return True
        else:
            logger.error(f"Invalid Discord token. Status code: {response.status_code}")
            return False
    except requests.RequestException as e:
        logger.error(f"Error while checking Discord token: {e}")
        return False

def check_target_account(token: str, target_user_id: str) -> bool:
    """Check if the target account is valid and accessible with the provided token."""

    url = f"https://discord.com/api/v9/users/{target_user_id}/profile"
    headers = {"Authorization": token}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            logger.info(f"Target account {target_user_id} is valid")
            return True
        else:
            logger.error(f"Invalid target account. Status code: {response.status_code}")
            return False
    except requests.RequestException as e:
        logger.error(f"Error while checking target account: {e}")
        return False


async def discord_monitor(token: str):
    logger.info("Starting Discord monitor...")
    