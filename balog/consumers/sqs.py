from __future__ import unicode_literals
import json
import collections
import functools
import threading
import logging
import time

import boto.sqs
from boto.sqs.message import RawMessage

from ..records.facility import FacilityRecordSchema

# Notice: this logger should be configured carefully
logger = logging.getLogger(__name__)


# TODO: define a base class?
class SQSEngine(object):
    """Event processing engine for polling Amazon SQS queues

    """

    def __init__(
        self,
        hub,
        region,
        aws_access_key_id,
        aws_secret_access_key,
        polling_period=1,
        num_messages=10,
        consumer_decorator=None,
    ):
        self.hub = hub
        # aws credentials
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        #: polling period in seconds
        self.polling_period = polling_period
        #: maximum number of messages to get at once
        self.num_messages = num_messages
        #: decorator of consumer consumer_decorator
        self.consumer_decorator = consumer_decorator
        if self.consumer_decorator is None:
            self.consumer_decorator = lambda consumer: consumer

        self.running = False

    def _poll_topic(self, topic, consumers):
        """Poll events from SQS

        """
        logger.info(
            'Polling %s for consumers %s',
            topic, consumers,
        )
        schema = FacilityRecordSchema()
        queue = self.conn.get_queue(topic)
        queue.set_message_class(RawMessage)
        while self.running:
            msgs = queue.get_messages(
                num_messages=self.num_messages,
                wait_time_seconds=self.polling_period,
            )
            for msg in msgs:
                json_data = json.loads(msg.get_body())
                event = schema.deserialize(json_data)
                logger.debug('Processing event %r', event)
                # Notice: Since we're processing logs, if we generate
                # log and that will be consumed by this loop, it may
                # end up with flood issue (one log generates more logs)
                # so, we should be careful, do not generate log record
                # from this script
                for consumer in consumers:
                    decorated_consumer = self.consumer_decorator(consumer)
                    decorated_consumer.func(event)
                # delete it from queue
                queue.delete_message(msg)

    def run(self):
        self.running = True
        self.conn = boto.sqs.connect_to_region(
            self.region,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )
        # map topic name (queue name) to consumers
        topic_to_consumers = collections.defaultdict(list)
        for consumer in self.hub.consumers:
            decorated_consumer = self.consumer_decorator(consumer)
            topic_to_consumers[decorated_consumer.topic].append(consumer)

        # create threads for consuming events from SQS
        threads = []
        for topic, consumers in topic_to_consumers.iteritems():
            thread = threading.Thread(
                target=functools.partial(self._poll_topic, topic, consumers),
                name='polling-topic-{}-worker'.format(topic)
            )
            thread.daemon = True
            threads.append(thread)

        # start all threads
        for thread in threads:
            thread.start()

        try:
            while self.running:
                time.sleep(1)
        except (SystemExit, KeyboardInterrupt):
            self.running = False
            logger.info('Stopping SQS engine')

        for thread in threads:
            thread.join()
        logger.info('Stopped SQS engine')