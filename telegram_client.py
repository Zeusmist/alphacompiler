import os
import json
from telethon import TelegramClient, events
from telethon.tl.types import InputPeerChannel
from telethon.tl.functions.channels import GetFullChannelRequest
from lib.config import (
    telegram_api_id,
    telegram_api_hash,
    telegram_phone_number,
    telegram_channel_usernames,
)
from gemini_llm import analyze_with_gemini


async def download_image(message, client):
    if message.photo:
        path = await message.download_media()
        print(f"Photo downloaded to {path}")
        return path
    elif message.document and message.document.mime_type.startswith("image"):
        path = await message.download_media()
        print(f"Image document downloaded to {path}")
        return path


async def message_handler(event):
    message = event.message
    image_path = await download_image(message, event.client) if message.media else None

    analysis_result = await analyze_with_gemini(image_path, message.text)

    print(f"Message: {message.text}, image_path: {image_path}")

    if analysis_result:
        if (
            analysis_result["is_alpha_call"]
            and analysis_result["token_ticker"]
            and analysis_result["network"]
        ):
            # Add the channel name, url and date to the result
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

            print(f"Alpha call detected: {json.dumps(analysis_result, indent=2)}")

            # Here you could save the result to a database or file
        else:
            print(
                "Message discarded: Not an alpha call or missing required information"
            )
            print(f"Analysis result: {json.dumps(analysis_result, indent=2)}")
    else:
        print("Failed to analyze message")

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
