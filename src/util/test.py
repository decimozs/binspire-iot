import logging
import coloredlogs
import random
import json
import asyncio
from lib.mqtt_client import MQTTClient
from lib.db import Database
from lib.firebase import messaging
from lib.ultrasonic_sensor import UltrasonicSensor

logger = logging.getLogger(__name__)
coloredlogs.install(
    level="DEBUG", logger=logger, fmt="%(asctime)s [%(levelname)s] %(message)s"
)

TRIG = 23
ECHO = 24
sensor = UltrasonicSensor(trig_pin=TRIG, echo_pin=ECHO)


async def test_simulate_trashbin(id, db: Database):
    if not db.pool:
        logger.critical("Database connection is not established.")
        raise RuntimeError("Database connection is not established.")

    if id is None:
        logger.critical("Trashbin ID is None.")
        raise ValueError("Trashbin ID cannot be None.")

    logger.debug(f"Starting simulation for trashbin ID: {id}")

    client = MQTTClient(client_id=f"trashbin_{id}")
    client.connect()
    topic = f"trashbin/{id}/status"
    logger.info(f"{id}: MQTT client connected and publishing to topic '{topic}'")

    try:
        while True:
            waste_level = random.randint(0, 100)
            weight_level = round(random.uniform(0, 30), 2)
            battery_level = random.randint(0, 100)
            urgency_score = (waste_level / 100) * 0.6 + (weight_level / 30) * 0.4

            logger.debug(
                f"{id}: Simulated values - Waste: {waste_level}%, Weight: {weight_level}kg, Battery: {battery_level}%, Urgency: {urgency_score:.2f}"
            )

            async with db.pool.acquire() as connection:
                trashbin = await connection.fetchrow(
                    "SELECT * FROM trashbins WHERE id = $1", id
                )

                if id == "-_gdHI4_ijhT6-O5uEAZ9":
                    distance = sensor.get_distance()

                    if distance is None:

                        logger.error(
                            f"{id}: Failed to read distance from ultrasonic sensor."
                        )

                        await asyncio.sleep(60)
                        continue

                    waste_level = int((distance / 100) * 100)
                    logger.debug(
                        f"{id}: Sensor distance: {distance} cm → Waste level: {waste_level}%"
                    )

                if not trashbin:
                    logger.warning(f"{id}: Trashbin not found in database.")
                    await asyncio.sleep(20)
                    continue

                if waste_level > 20 and trashbin["is_collected"]:
                    logger.info(
                        f"{id}: Waste level is {waste_level}%, resetting is_collected to FALSE."
                    )
                    await connection.execute(
                        "UPDATE trashbins SET is_collected = FALSE WHERE id = $1", id
                    )
                    trashbin = dict(trashbin)
                    trashbin["is_collected"] = False

                if urgency_score >= 0.8 and not trashbin["is_scheduled"]:
                    logger.warning(
                        f"{id}: High urgency detected (Score: {urgency_score:.2f}), scheduling collection."
                    )
                    await connection.execute(
                        "UPDATE trashbins SET is_scheduled = TRUE, scheduled_at = NOW() WHERE id = $1",
                        id,
                    )
                    trashbin = dict(trashbin)
                    trashbin["is_scheduled"] = True

                    rows = await connection.fetch(
                        """
                        SELECT n.fcm_token
                        FROM notifications n
                        JOIN users u ON u.id = n.user_id
                        WHERE u.role = 'collector' AND n.fcm_token IS NOT NULL
                    """
                    )

                    tokens = list(
                        {row["fcm_token"] for row in rows if row["fcm_token"]}
                    )

                    if tokens:
                        try:
                            fcm_message = messaging.MulticastMessage(
                                notification=messaging.Notification(
                                    title="Urgent Bin Alert",
                                    body=f"{trashbin['name'] or 'A bin'} needs urgent collection!",
                                ),
                                webpush=messaging.WebpushConfig(
                                    fcm_options=messaging.WebpushFCMOptions(
                                        link=f"https://binspire-web.onrender.com/dashboard/map?trashbin_id={trashbin['id']}&view_trashbin=true"
                                    )
                                ),
                                tokens=tokens,
                            )

                            response = messaging.send_each_for_multicast(fcm_message)
                            logger.info(
                                f"{id}: Sent notification to {response.success_count} collectors."
                            )
                            if response.failure_count > 0:
                                logger.warning(
                                    f"{id}: {response.failure_count} notifications failed."
                                )
                        except Exception as e:
                            logger.error(
                                f"{id}: Failed to send push notification - {e}",
                                exc_info=True,
                            )

            message = {
                "trashbin": {
                    "id": trashbin["id"],
                    "name": trashbin["name"] or "Unknown",
                    "location": trashbin["location"] or "Unknown",
                    "isOperational": trashbin["is_operational"],
                    "isCollected": trashbin["is_collected"],
                    "latitude": (
                        float(trashbin["latitude"])
                        if trashbin["latitude"] is not None
                        else 0.0
                    ),
                    "longitude": (
                        float(trashbin["longitude"])
                        if trashbin["longitude"] is not None
                        else 0.0
                    ),
                },
                "status": {
                    "wasteLevel": waste_level,
                    "weightLevel": weight_level,
                    "batteryLevel": battery_level,
                },
            }

            json_message = json.dumps(message, indent=2)
            client.publish(topic, json_message)
            logger.info(f"{id}: Published MQTT message to topic '{topic}'")

            await asyncio.sleep(20)

    except asyncio.CancelledError:
        logger.warning(f"{id}: Task cancelled, disconnecting client.")
        client.disconnect()

    except Exception as e:
        logger.error(f"{id}: Unexpected error occurred - {e}", exc_info=True)
        client.disconnect()
