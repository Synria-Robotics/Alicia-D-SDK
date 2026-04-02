# RTM Bridge

This directory contains a two-process bridge for:

- `Alicia-D ws -> Agora RTM`
- `Agora RTM -> Alicia-M ws`

RTM runs inside a local Chrome page started by Playwright. Node is only used to:

- start Chrome
- register devices with `/robots/connect`
- forward browser logs to the terminal

## Files

- `publish_d_ws_to_rtm.js`: poll leader ws with `{"type":"get.state"}` and publish state to RTM.
- `subscribe_rtm_to_m_ws.js`: subscribe RTM state and forward to follower ws with `{"type":"cmd.movej", ...}`.

## Install

```bash
cd examples/rtm_bridge
npm install
```

## Run publisher

```bash
cd examples/rtm_bridge
node publish_d_ws_to_rtm.js \
  --app-id 54f9b64b82204d74b35e3b9c5430a020 \
  --leader-ws ws://localhost:8000/robots/ws//dev/cu.usbmodem5B7B0460781 \
  --channel alicia-teleop \
  --frequency 50 \
  --verbose
```

## Run subscriber

```bash
cd examples/rtm_bridge
node subscribe_rtm_to_m_ws.js \
  --app-id 54f9b64b82204d74b35e3b9c5430a020 \
  --follower-ws ws://localhost:8000/robots/ws//dev/cu.usbmodem5B7A1009171 \
  --channel alicia-teleop \
  --speed 573 \
  --execute-frequency 50 \
  --recv-csv rtm_received.csv \
  --send-csv m_commands.csv \
  --verbose
```

## Compare CSV

```bash
cd examples/rtm_bridge
node compare_csv.js \
  --recv rtm_received.csv \
  --send m_commands.csv
```

## Token

If your Shengwang project has App Certificate enabled, both processes must provide RTM token:

```bash
export AGORA_RTM_TOKEN=<your_rtm_token>
```

Or pass `--rtm-token <token>`.

## Notes

- This implementation uses RTM Message Channel.
- Recommended configuration is fixed `50 Hz` publish and fixed `50 Hz` execute.
- The publisher samples leader state into a FIFO queue at fixed `50 Hz`, and RTM sends from that queue.
- The subscriber pushes RTM messages into a FIFO queue immediately, and the executor consumes that queue at fixed `50 Hz`.
- `seq` is still recorded and checked; gaps are logged before execution.
- If follower execution is slower than input rate, queue latency will accumulate instead of skipping ahead.
- The subscriber writes RTM receive rows to `rtm_received.csv` and follower command rows to `m_commands.csv` by default.
- No automatic home movement is performed.
- Default Chrome path is `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.
