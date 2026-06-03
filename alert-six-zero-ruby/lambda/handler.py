import json
import boto3
import os
import logging
from botocore.exceptions import ClientError
from alerter import Alerter


def main(event, context):

    # Initialise logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.info("requests: " + json.dumps(event))

    # SNS client and ARN
    sns_client = boto3.client("sns")
    topic_arn = os.environ.get("TOPIC_ARN")

    # Run alerter
    alerter = Alerter()

    # Choose strings based on run type
    is_daily = "Daily" in event["resources"][0]
    if is_daily:
        subject = "DAILY CHECK - ALERTER WORKING"
        freq_text = "Daily Check"
    else:
        subject = alerter.subject
        freq_text = "Regular Check"

    # Main logic
    try:
        # Email when triggered, or daily check run
        if alerter.trigger_alert or is_daily:
            # Publish email
            sent_message = sns_client.publish(
                TopicArn=topic_arn,
                Message=alerter.message,
                Subject=subject,
            )

            if sent_message is not None:
                logger.info(f"Success - Message ID: {sent_message['MessageId']}")
            else:
                logger.error("Failed to publish message")

        # Additional log info
        # logger.info(f"{freq_text} - alerter.trigger_alert: {alerter.trigger_alert}")
        print(f"{freq_text} - alerter.trigger_alert: {alerter.trigger_alert}")

        return {"statusCode": 200}

    except ClientError as e:
        logger.error(e)
        return None
