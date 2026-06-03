from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as targets,
    BundlingOptions,
    aws_sns as sns,
)
from constructs import Construct


class AlertSixZeroRubyStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        fn = lambda_.Function(
            self,
            "Singleton",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(300),
            handler="handler.main",
            code=lambda_.Code.from_asset(
                "lambda",
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install --no-cache -r requirements.txt -t /asset-output && cp -au . /asset-output",
                    ],
                ),
            ),
        )

        topic = sns.Topic(self, "Topic")

        topic.grant_publish(fn)

        fn.add_environment("TOPIC_ARN", str(topic.topic_arn))

        sns.Subscription(
            self,
            "Subscription",
            topic=topic,
            endpoint="vilberto.noerjanto@gmail.com",
            protocol=sns.SubscriptionProtocol.EMAIL,
        )

        rule_hourly = events.Rule(
            self,
            "RuleRegular",
            # schedule=events.Schedule.rate(Duration.minutes(5))
            schedule=events.Schedule.cron(minute="*/5"),
            # schedule=events.Schedule.cron(minute='0')
        )

        rule_daily = events.Rule(
            self,
            "RuleDaily",
            # schedule=events.Schedule.rate(Duration.minutes(10))
            schedule=events.Schedule.cron(minute="0", hour="8"),
        )

        rule_hourly.add_target(targets.LambdaFunction(fn))
        rule_daily.add_target(targets.LambdaFunction(fn))
