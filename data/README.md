# Synthetic CloudTrail dataset

This directory contains deterministic, synthetic AWS CloudTrail-style events
for developing and evaluating CloudSec Copilot. It contains no real AWS account
activity, credentials, or personal data. Account identifiers and IP addresses
use documentation-only values.

## Files

- `cloudtrail_events.json`: ten input events in a CloudTrail-like `Records`
  envelope.
- `root_login_without_mfa_labels.json`: expected result and rationale for every
  event under the first detection rule.
- `additional_security_events.json`: eight positive and negative CloudTrail-style
  events covering four additional security scenarios.
- `additional_security_event_labels.json`: expected rule IDs and rationale for
  every event in the additional dataset.

## First detection rule

`AWS-IAM-001` should match an event only when all of the following are true:

1. `userIdentity.type` is `Root`.
2. `eventSource` is `signin.amazonaws.com`.
3. `eventName` is `ConsoleLogin`.
4. `responseElements.ConsoleLogin` is `Success`.
5. `additionalEventData.MFAUsed` is `No`.

The dataset deliberately includes failed root logins, root API calls, IAM-user
logins, and successful root logins with MFA so the detector cannot pass by
checking only one or two fields.

## Expected distribution

- Total events: 18
- Positive events: 6
- Negative events: 12
- Detection rules: 5
