balog
=====

[![Build Status](https://travis-ci.org/balanced/balog.svg?branch=master)](https://travis-ci.org/balanced/balog)

Balanced event logging schema and library

Log schema design goals
=======================

 - Schema version annotated
 - Provide sufficient information about the event
 - Open and close (be flexible, avoid unnecessary change to schema)

Design rationals
================

OSI Network Model Structure
---------------------------

Data in the log can be divided into two major groups, one is the meta data,
which is the data about the event. The another group is the log for application 
itself. In most cases, applications should only be interested in the 
application log itself. And the logging facility should only be interested in 
how to handle the whole event rather than to consume the content of application 
log. Also, since schema of application can variant, we don't want change the
whole schema everytime when application log is change. Consider these issues,
one idea come to my mind is Internet OSI model is actually dealing with the
same issue. It's like TCP/IP protocol doesn't need to know the content of
application layer. Similarly, logging facility doesn't have to know the content
of application log. With this idea in mind, I define two layers for our logging
system.

 - Facility layer
 - Application layer

Facility layer is all about the event, when it is generated, who emited this
event, what's its routing tag and etc. Application layer is all about
application data, like a dispute is processed, a debit is created and etc.

Facility layer
==============

Header
------

### id (required)

The unique GUID for this event, starts with `LG` prefix.

### channel (required)

The tag for routing event, e.g. `justitia.models.disputes.created`.

### timestamp (required)

Creating time for this event, should be in ISO8601 format with UTC timezone.

### schema (required)

A string indicates what version this schema is, follow [Semantic Versioning 2.0.0](http://semver.org).

### payload (required)

Payload of this log.

### open_content (optional)

Open content of this log.

### context (optional)

Context is a dict which contains information regarding the context when this
log is emited. Optional field can be

 - fqdn - The host name
 - application - Name of running application
 - application_version - The version of curnning application

### composition (optional)

Is this event a composited event. If this field is not present, then composition
value is default to `false`.

TODO

Payload
-------

TODO

Open content
------------

TODO

Usage
=====

To produce a log, here you can write

```python
from balog import get_logger
balogger = get_logger(__name__)

balogger.info('done', payload={
    'cls_type': 'metrics',
    'values': [
        {'name': 'total', 'value': 123},
        {'name': 'succeeded', 'value': 456},
        {'name': 'failed', 'value': 789},
    ],
})
```

The channel name will be the logger name + the given suffix name, in the above example, the say if the `__name__` is 
`justitia.scripts.process_results` here, then the channel name will be `justitia.scripts.process_results.done`. If you want to overwrite the channel name, you can also pass `channel` argument to balog logging methods.

To consume events, you can use `consumer_config` like this

```python
from balog.consumers import consumer_config

@consumer_config(
    topic='balanced-justitia-events-{env}',
    cls_type='metrics',
    version='<1.0',
)
def process_metrics(settings, event):
    pass
```

This `consumer_config` decorator is mainly for declaring what this consumer wants, in the example above, since want to subscribe the queue `balanced-justitia-events-develop` or `balanced-justitia-events-prod`, so we set the topic to `'balanced-justitia-events-{env}'`, for the `{env}` placeholder, we will talk about that later. And then we're only interested in `metrics` type events, so we set `cls_type` to `metrics`. Then we don't want to process events that's not compatible, so we set the `version` to `<1.0`. 

With these configured consumers, to process events, you need to use `ConsumerHub`. It is basically a collection of consumers. It provides scanning function to make collecting consumers pretty easy. For example, here you can write

```python
import justitia
from balog.consumers import ConsumerHub

hub = ConsumerHub()
hub.scan(justitia)
```

By doing that, you have all consuemrs in the hub.
