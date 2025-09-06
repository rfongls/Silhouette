# Interop Dashboard

## MLLP Send

`/api/interop/mllp/send` accepts `messages` either as a JSON array of HL7 strings or as a single string containing one or more HL7 messages separated by blank lines. The server splits on blank lines and sends each message individually.
