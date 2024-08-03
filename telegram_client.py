import os
import json
import aiohttp
from telethon import TelegramClient, events
from telethon.tl.types import InputPeerChannel
from lib.config import (
    telegram_api_id,
    telegram_api_hash,
    telegram_phone_number,
    telegram_channel_usernames,
)
from gemini_llm import analyze_with_gemini
from db.db_operations import db_operations


async def download_image(message, client):
    if message.photo:
        path = await message.download_media("downloaded_media")
        return path
    elif message.document and message.document.mime_type.startswith("image"):
        path = await message.download_media("downloaded_media")
        return path


async def fetch_token_info_from_dexscreener(ticker):
    async with aiohttp.ClientSession() as session:
        url = f"https://api.dexscreener.io/latest/dex/search?q={ticker}"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data["pairs"] and len(data["pairs"]) > 0:
                    pair = data["pairs"][0]
                    return {
                        "token_address": pair["baseToken"]["address"],
                        "token_name": pair["baseToken"]["name"],
                        "token_image": pair.get("info", {}).get("imageUrl"),
                        "network": pair["chainId"],
                    }
    return None


async def message_handler(event):
    message = event.message
    image_path = await download_image(message, event.client) if message.media else None

    analysis_result = await analyze_with_gemini(image_path, message.text)

    try:
        if analysis_result:
            if analysis_result["is_alpha_call"] and analysis_result["token_ticker"]:
                # Remove $ from ticker if present
                if analysis_result["token_ticker"].startswith("$"):
                    analysis_result["token_ticker"] = analysis_result["token_ticker"][
                        1:
                    ]

                # Check for missing network
                if not analysis_result.get("network"):
                    network = await db_operations.token_repo.get_network_for_ticker(
                        analysis_result["token_ticker"]
                    )
                    # network might be null
                    if network and network != "null":
                        print(
                            f"Network found if: {analysis_result['token_ticker']}: {network}"
                        )
                        analysis_result["network"] = network

                # Fetch token info from DexScreener if network or address is missing
                if not analysis_result.get("network") or not analysis_result.get(
                    "token_address"
                ):
                    token_info = await fetch_token_info_from_dexscreener(
                        analysis_result["token_ticker"]
                    )
                    print(
                        f"Token info from DexScreener: {json.dumps(token_info, indent=2)}"
                    )
                    if token_info:
                        analysis_result["token_address"] = token_info["token_address"]
                        analysis_result["token_name"] = token_info["token_name"]
                        if token_info["token_image"]:
                            analysis_result["token_image"] = token_info["token_image"]
                        if not analysis_result.get("network"):
                            analysis_result["network"] = token_info["network"]

                channel = await event.get_chat()
                analysis_result["channel_name"] = channel.title
                if channel.username:  # Public channel
                    analysis_result["message_url"] = (
                        f"https://t.me/{channel.username}/{message.id}"
                    )
                else:  # Private channel
                    analysis_result["message_url"] = (
                        f"https://t.me/c/{channel.id}/{message.id}"
                    )
                analysis_result["date"] = message.date.isoformat()

                # Only save the alpha call if we have all required information
                if analysis_result.get("network") and analysis_result.get(
                    "token_address"
                ):
                    print(
                        f"Alpha call detected: {json.dumps(analysis_result, indent=2)}"
                    )
                    await db_operations.token_repo.save_alpha_call(analysis_result)
                else:
                    print("Message discarded: Missing network or token_address")
                    print(
                        f"Incomplete analysis result: {json.dumps(analysis_result, indent=2)}"
                    )
            else:
                print(
                    "Message discarded: Not an alpha call or missing required information"
                )
        else:
            print("Failed to analyze message")
    except Exception as e:
        print(f"An error occurred: {e}")

    if image_path:
        os.remove(image_path)  # Clean up the downloaded image


async def start_telegram_client():
    client = TelegramClient("session", telegram_api_id, telegram_api_hash)

    try:
        await client.start(phone=telegram_phone_number)
        print("Client Created")

        if not await client.is_user_authorized():
            await client.send_code_request(telegram_phone_number)
            await client.sign_in(telegram_phone_number, input("Enter the code: "))

        await db_operations.connect()

        channels = []
        for username in telegram_channel_usernames:
            channel = await client.get_entity(username)
            channels.append(InputPeerChannel(channel.id, channel.access_hash))

        # Register the message handler
        client.add_event_handler(message_handler, events.NewMessage(chats=channels))

        print("Listening for new messages...")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await client.disconnect()
        await db_operations.close()
