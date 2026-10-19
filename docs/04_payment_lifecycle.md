What is a payment?
What is a payment attempt?
Why can one payment have multiple attempts?
What uniquely identifies a payment attempt?
What information do we need about an attempt to determine whether it succeeded, failed, or was retried?

Answers
1) A payment represents the financial intent to transfer a specified amount of money from a payer to a recipient.
2) A payment attempt is one individual execution of a payment through a processor.
3) One payment can have multiple attempt because of the number of trials payment may go through before finally successful.
4) payment_attempt_id uniquely identifies each payment attempt and serves as the primary key.
5) The information needed about attempt can be detemined by the fields from the business questions and lifecycle bahavior we need to represent.

Proposed Payment Attempts Fields are:
| Field                      | Purpose                             |
| -------------------------- | ----------------------------------- |
| `payment_attempt_id`       | Unique identifier for the attempt   |
| `payment_id`               | Links attempt to the parent payment |
| `attempt_number`           | Sequence of the attempt             |
| `processor`                | Processor handling the attempt      |
| `payment_method`           | Method used                         |
| `status`                   | Result/state of the attempt         |
| `error_code`               | Failure reason when applicable      |
| `processor_transaction_id` | External processor reference        |
| `created_at`               | Attempt start time                  |
| `completed_at`             | Attempt completion time             |


why amount_minor and currency belong to payments rather than payment_attempts.
amount_minor and currency belong to the payment because they describe the original financial intent. Multiple payment attempts are different processing executions of the same payment, so repeating these attributes in every attempt could introduce unnecessary duplication and inconsistencies.

Payment Attempt Business Rules(UNIQUE(payment_id, attempt_number))
| Rule                                                  | Decision                                                          |
| ----------------------------------------------------- | ----------------------------------------------------------------- |
| A payment can have one attempt                        | **Yes**                                                           |
| A payment can have multiple attempts                  | **Yes**                                                           |
| `attempt_number` can repeat for the same payment      | **No**                                                            |
| Different payments can have the same `attempt_number` | **Yes**                                                           |
| Failed attempt's `completed_at`                       | Records processing completion time; NULL if still processing      |
| SUCCESS attempt has `error_code`                      | **No**                                                            |
| FAILED attempt has `error_code`                       | **Yes**; reqiure when the failure has a known reason
      |
| Every attempt must have `processor_transaction_id`    | **No**; required for successful processing, optional for failures |

**Schema**
payment_attempts
-----------------------------
payment_attempt_id       PK
payment_id               FK
attempt_number
processor
payment_method
status
error_code
processor_transaction_id
created_at
completed_at

Constraints:
PRIMARY KEY (payment_attempt_id)

FOREIGN KEY (payment_id)
→ payments(payment_id)

UNIQUE(payment_id, attempt_number)

**Version1** **Synthetic** **system**
| Failure                 | Retry decision | Attempt behavior  |
| ----------------------- | -------------- | ----------------- |
| `INSUFFICIENT_FUNDS`    | No             | Stop              |
| `CARD_DECLINED`         | No             | Stop              |
| `INVALID_ACCOUNT`       | No             | Stop              |
| `PROCESSOR_TIMEOUT`     | Yes            | Retry after delay            |
| `PROCESSOR_UNAVAILABLE` | Yes            | Retry after delay |
| `NETWORK_ERROR`         | Yes            | Retry             |

Retryable failures

PROCESSOR_TIMEOUT
PROCESSOR_UNAVAILABLE
NETWORK_ERROR

Non-retryable failures

INSUFFICIENT_FUNDS
CARD_DECLINED
INVALID_ACCOUNT

Retry limit

A payment may have a maximum of 3 total attempts. A delay/backoff is applied before subsequent attempts.

A retryable failure permits the next attempt to use either the same processor or another available processor. Processor selection will be modeled as a routing decision, not as a random independent attribute.

For example:
P001
 ├── Attempt 1 → NETWORK_ERROR
 ├── Attempt 2 → PROCESSOR_TIMEOUT
 └── Attempt 3 → SUCCESS

Overall payment → SUCCESS

P002
 ├── Attempt 1 → NETWORK_ERROR
 ├── Attempt 2 → NETWORK_ERROR
 └── Attempt 3 → NETWORK_ERROR

Overall payment → FAILED

V1 SUCCESS attempt distribution
|  Attempts | Percentage | Interpretation              |
| --------: | ---------: | --------------------------- |
|         1 |        65% | Successful on first attempt |
|         2 |        25% | One retry before success    |
|         3 |        10% | Two retries before success  |
| **Total** |   **100%** |                             |

This gives us useful data for analyzing:

first-attempt success rate
retry rate
retry recovery
average attempts per successful payment
processor reliability
payment latency

Failed Payment Lifecycle Distribution — V1

Among payments classified as FAILED, 70% will fail on the first attempt, 20% will require two attempts before ultimately failing, and 10% will require three attempts before ultimately failing. These are synthetic assumptions intended to create a varied payment lifecycle for testing and analytics; they are not real-world benchmarks.

Our V1 pending rule

| Payment status | Attempt pattern                                                                |
| -------------- | ------------------------------------------------------------------------------ |
| **SUCCESS**    | 65% → 1 attempt, 25% → 2 attempts, 10% → 3 attempts                            |
| **FAILED**     | 70% → 1 attempt, 20% → 2 attempts, 10% → 3 attempts                            |
| **PENDING**    | 1 unresolved attempt; `status=PENDING`, `error_code=NULL`, `completed_at=NULL` |


V1 network-related processing conditions are the assumed cause of pending states.

That keeps the semantics clean:

FAILED → processing ended unsuccessfully
PENDING → processing has not reached a final state
SUCCESS → processing completed successfully

Attempt status definition.
| Status    | Meaning                                        |
| --------- | ---------------------------------------------- |
| `SUCCESS` | Processor successfully completed the attempt   |
| `FAILED`  | Processor completed the attempt unsuccessfully |
| `PENDING` | Processing has not reached a final state       |

Lifecycle invariant:
SUCCESS payment
→ final attempt must be SUCCESS

FAILED payment
→ final attempt must be FAILED

PENDING payment
→ unresolved attempt remains PENDING

V1 attempt-generation logic
Payment
   ↓
Choose payment method
   ↓
Choose processor
   ↓
Generate attempt
   ↓
SUCCESS?
 ├── YES → stop
 │
 └── NO
      ↓
Retryable?
 ├── NO → stop as FAILED
 │
 └── YES
      ↓
Attempts < 3?
 ├── NO → stop as FAILED
 │
 └── YES
      ↓
Wait using backoff
      ↓
Choose processor
      ↓
Generate next attempt

For processor selection:
Attempt 1
→ weighted selection

Retry after 1 failure
→ same processor

Retry after 2 consecutive failures
→ switch processor


**Locked** **error**-**code** **rule**

For any FAILED attempt that is still eligible for retry, randomly select one of:
NETWORK_ERROR
PROCESSOR_TIMEOUT
PROCESSOR_UNAVAILABLE

with equal probability:
NETWORK_ERROR          → 33.33%
PROCESSOR_TIMEOUT      → 33.33%
PROCESSOR_UNAVAILABLE  → 33.33%

For example:
Payment P1001
│
├── Attempt 1 → FAILED → NETWORK_ERROR
├── Attempt 2 → FAILED → PROCESSOR_TIMEOUT
└── Attempt 3 → SUCCESS → NULL

**we've **established**:

Attempt 1 processor = parent's existing processor
Attempt 1 starts 0–2 seconds after payment creation
SUCCESS takes 2–10 seconds
FAILED takes 2–15 seconds
PENDING has no completed_at
Successful lifecycle → failures first, then SUCCESS
Failed lifecycle → all attempts FAILED
Pending lifecycle → one PENDING attempt
Retryable failures use the three retryable error codes equally
SUCCESS → error_code = NULL
PENDING → error_code = NULL

Locked rule

The relationship will be:

payment_attempt_id
        ↓
deterministic transformation
        ↓
processor_transaction_id

For example:

payment_attempt_id = ATT-P1001-001
processor = STRIPE

→ processor_transaction_id = pi_ATT-P1001-001

For another processor:
payment_attempt_id = ATT-P1001-002
processor = ADYEN

→ processor_transaction_id = ADYEN_ATT-P1001-002
The exact formatting is something we'll implement cleanly when we write the helper function.

1. Lock the processor-routing rules

Our processors are:

STRIPE
ADYEN
FLUTTERWAVE

The fallback order is:

STRIPE → ADYEN → FLUTTERWAVE

When a processor switch is required, we move to the next processor in this order, skipping the processor already used.

| Current processor | Next processor |
| ----------------- | -------------- |
| `STRIPE`          | `ADYEN`        |
| `ADYEN`           | `FLUTTERWAVE`  |
| `FLUTTERWAVE`     | `STRIPE`       |
This is a cyclic fallback order. It lets us determine the next processor consistently, regardless of which processor handled the initial attempt.

2. **How the routing works**

Our existing rules determine when to switch processors:

Attempt 1 uses the processor assigned to the parent payment.
After one retryable failure, retry using the same processor.
After two consecutive retryable failures, switch processors.
A non-retryable failure terminates the payment.
Never exceed three total attempts.

Example 1: Payment succeeds on Attempt 2
Payment P1001
Initial processor: STRIPE

Attempt 1 → STRIPE → FAILED / NETWORK_ERROR
Attempt 2 → STRIPE → SUCCESS
Only one retryable failure occurred, so the processor remains Stripe.

Example 2: Payment succeeds on Attempt 3
Payment P1002
Initial processor: STRIPE

Attempt 1 → STRIPE → FAILED / NETWORK_ERROR
Attempt 2 → STRIPE → FAILED / PROCESSOR_TIMEOUT
Attempt 3 → ADYEN → SUCCESS
Two consecutive retryable failures occurred, so the system switches to Adyen.

Example 3: Payment starts with Flutterwave
Payment P1003
Initial processor: FLUTTERWAVE

Attempt 1 → FLUTTERWAVE → FAILED / NETWORK_ERROR
Attempt 2 → FLUTTERWAVE → FAILED / PROCESSOR_TIMEOUT
Attempt 3 → STRIPE → SUCCESS
The cyclic fallback rule sends the third attempt to Stripe.

*Important:* These are synthetic examples, not actual processor performance statistics.

**The attempt format is:**
{payment_id}-ATT-{attempt_number}

For example, PAY-1001-ATT-002 identifies the second attempt associated with payment PAY-1001.

Here is the policy we will implement:

A payment can have a maximum of three total attempts.
Only retryable failures can trigger another attempt.
Non-retryable errors terminate the lifecycle immediately.
Retryable failures can trigger another attempt only when the attempt limit has not been reached.
Retry delays use exponential backoff: approximately 5 seconds before the first retry and 10 seconds before the second, with small random jitter.
After the third attempt fails, the payment becomes FAILED, and no fourth attempt is generated.
Delayed recovery after the lifecycle ends is a future enhancement.

These rules will keep our synthetic data consistent and make the system easier to test.

**Helper functions we need:**

determine_payment_lifecycle()
is_retryable_error()
determine_attempt_status()
select_processor()
create_attempt_id()
select_error_code()

The goal is to coordinate these functions into one generator that creates valid attempt records.

**The control flow**

The generator should follow this general sequence:
START
  |
  v
Initialize lifecycle state
  |
  v
Determine the current attempt
  |
  v
Determine the attempt outcome
  |
  v
Generate the appropriate error code
  |
  v
Create the attempt record
  |
  v
Did the attempt succeed?
  | Yes
  +----------> STOP
  |
  No
  v
Is the attempt pending?
  | Yes
  +----------> STOP
  |
  No
  v
Is the error retryable?
  | No
  +----------> STOP
  |
  Yes
  v
Have we reached the maximum of 3 attempts?
  | Yes
  +----------> STOP
  |
  No
  v
Update failure counter and processor routing
  |
  v
Calculate the next attempt's timestamp
  |
  v
Generate the next attempt