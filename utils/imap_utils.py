import re
from typing import Optional
import asyncio
from loguru import logger
from imap_tools import MailBox, AND
from config import settings


async def check_if_email_valid(
        imap_server: str,
        email: str,
        password: str,
) -> bool:
    logger.info(f"Account: {email} | Checking if email is valid...")
    try:
        # Use to_thread since MailBox is synchronous
        await asyncio.to_thread(lambda: MailBox(imap_server).login(email, password))
        return True
    except Exception as error:
        logger.error(f"Account: {email} | Email is invalid (IMAP): {error}")
        return False


async def check_email_for_link(
        imap_server: str,
        email: str,
        password: str,
        receiver_email: str,
        max_attempts: int = 3,
        delay_seconds: int = 20,
) -> Optional[tuple[str, MailBox, str]]:
    link_pattern = (
        r"https://www\.aeropres\.in/chromeapi/dawn/v1/user/verifylink\?key=[a-f0-9-]+"
    )
    logger.info(f"Account: {receiver_email} | Waiting 10 seconds before checking email...")
    await asyncio.sleep(10)
    logger.info(f"Account: {receiver_email} | Checking email for link...")

    try:
        folders_to_search = settings["icloud"]["folders_to_search"]

        async def search_in_folder(folder: str) -> Optional[tuple[str, MailBox, str]]:
            try:
                mailbox = await asyncio.to_thread(
                    lambda: MailBox(imap_server).login(email, password)
                )

                try:
                    if mailbox.folder.exists(folder):
                        logger.info(f"Account: {receiver_email} | Searching in folder: {folder}")
                        mailbox.folder.set(folder)
                        messages = list(mailbox.fetch(
                            criteria=AND(
                                from_="hello@dawninternet.com",
                                to=receiver_email.lower()
                            ),
                            reverse=True,
                            limit=10
                        ))

                        for msg in messages:
                            body = msg.text or msg.html
                            if body:
                                match = re.search(link_pattern, body)
                                if match:
                                    link = match.group(0)
                                    logger.info(f"Account: {receiver_email} | Link found in {folder}!")
                                    return link, mailbox, msg.uid

                        logger.debug(f"Account: {receiver_email} | No link found in {folder}")
                        mailbox.logout()
                        return None
                    else:
                        logger.debug(f"Account: {receiver_email} | Folder {folder} does not exist")
                        mailbox.logout()
                        return None

                except Exception as e:
                    mailbox.logout()
                    raise e

            except Exception as e:
                logger.error(f"Account: {receiver_email} | Error searching folder {folder}: {e}")
                return None

        for attempt in range(max_attempts):
            logger.info(f"Account: {receiver_email} | Attempt {attempt + 1}/{max_attempts}")

            for folder in folders_to_search:
                result = await search_in_folder(folder)
                if result:
                    return result

            if attempt < max_attempts - 1:
                logger.info(
                    f"Account: {receiver_email} | Link not found. Waiting {delay_seconds} seconds before next attempt..."
                )
                await asyncio.sleep(delay_seconds)

        logger.error(
            f"Account: {receiver_email} | Link not found in any folder after {max_attempts} attempts"
        )
        return None

    except Exception as error:
        logger.error(f"Account: {receiver_email} | Failed to check email for link: {error}")
        return None
