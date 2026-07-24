# Validation plan

The aim is to replace assumptions with evidence before committing to the full MVP.

## 1. Establish the real boundary

- Identify the systems, providers, credentials, data classes, and owners.
- Mark where customer data is stored, transmitted, logged, and deleted.
- Separate confirmed platform behaviour from intended behaviour.

## 2. Exercise one thin vertical slice

- Use representative, anonymised input.
- Call the intended API through the proposed authentication path.
- Validate the response against a strict contract.
- Record latency, token use, rate-limit headers, and failure behaviour.

## 3. Test the uncomfortable paths

- Malformed or incomplete provider output
- Timeout before a response
- Timeout after a side effect may have occurred
- Duplicate webhook or repeated request
- Unsupported evidence reference
- Cross-tenant evidence reference
- Low-confidence response
- Provider or model-version change

## 4. Produce decisions

Each finding should end in one of four states:

- **Go** - tested and suitable for the MVP.
- **Change** - feasible after a specific design amendment.
- **Defer** - valuable, but not required for the MVP.
- **Block** - conflicts with a hard platform, privacy, or reliability constraint.

The final report should retain the test evidence behind each decision.
