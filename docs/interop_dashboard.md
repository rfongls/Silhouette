# Interop Dashboard

## MLLP Send

`/api/interop/mllp/send` accepts `messages` either as a JSON array of HL7 strings or as a single string containing one or more HL7 messages separated by blank lines. The server splits on blank lines and sends each message individually.

### Dev MLLP Echo (local testing)

For a quick local ACK’ing listener:

```bash
python scripts/dev_mllp_echo.py --host 127.0.0.1 --port 2575
```

Then POST to the API:

```bash
curl -s http://localhost:8000/api/interop/mllp/send \
  -H "Content-Type: application/json" \
  -d '{"host":"127.0.0.1","port":2575,"messages":"MSH|^~\\\\&|SIL|HOSP|REC|HUB|202501010000||ADT^A01|X|P|2.4\\r\\nPID|1||12345^^^HOSP^MR||DOE^JOHN\\r\\n"}'
```

The echo server returns one ACK per frame and includes the inbound `MSH-10` value in `MSA-2`.
