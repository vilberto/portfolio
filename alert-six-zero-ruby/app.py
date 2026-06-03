#!/usr/bin/env python3
from aws_cdk import App
from infrastructure.stack import AlertSixZeroRubyStack

app = App()
AlertSixZeroRubyStack(app, "AlertSixZeroRubyStack")

app.synth()
