Payments



The generator must produce:



unique payment\_id

customer\_id

merchant\_id

amount

currency

payment status

creation timestamp

Payment attempts



Every attempt must:



belong to a valid payment

have a unique payment\_attempt\_id

have an attempt\_number

reference one processor

have a payment method

have a status

have timestamps

optionally have an error/decline reason

Payment events



Every event must:



have a unique event ID

belong to a payment

optionally belong to an attempt

have an event type

have an event timestamp



| Attribute            | Values | Distribution/Rule |

| -------------------- | ------ | ----------------- |

| Payment status       | ?      | ?                 |

| Payment method       | ?      | ?                 |

| Processor            | ?      | ?                 |

| Currency             | ?      | ?                 |

| Failure reason       | ?      | ?                 |

| Attempts per payment | ?      | ?                 |



