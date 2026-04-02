#!/usr/bin/env node

import { parseArgs } from 'node:util';
import fs from 'node:fs';
import { chromium } from 'playwright-core';
import {
  createBrowserHostServer,
  DEFAULT_APP_ID,
  DEFAULT_CHROME_PATH,
  connectDeviceViaRest,
  extractDeviceIdFromWsUrl,
  log,
  resolveAgoraRtcScriptPath,
  resolveAgoraRtmScriptPath,
} from './common.js';

function parseCli() {
  const { values } = parseArgs({
    options: {
      'app-id': { type: 'string', default: DEFAULT_APP_ID },
      'rtm-user-id': { type: 'string', default: `m-subscriber-${Date.now()}` },
      'rtm-token': { type: 'string', default: process.env.AGORA_RTM_TOKEN ?? '' },
      'channel': { type: 'string', default: 'alicia-teleop' },
      'topic': { type: 'string', default: 'teleop' },
      'follower-ws': { type: 'string' },
      'speed': { type: 'string', default: '573' },
      'execute-frequency': { type: 'string', default: '50' },
      'no-wait-ok': { type: 'boolean', default: false },
      'recv-csv': { type: 'string', default: 'rtm_received.csv' },
      'send-csv': { type: 'string', default: 'm_commands.csv' },
      'chrome': { type: 'string', default: DEFAULT_CHROME_PATH },
      'headed': { type: 'boolean', default: false },
      'verbose': { type: 'boolean', default: false },
      'help': { type: 'boolean', short: 'h', default: false },
    },
    allowPositionals: false,
  });

  if (values.help || !values['follower-ws']) {
    console.log(`Usage:
  node subscribe_rtm_to_m_ws.js --follower-ws ws://localhost:8000/robots/ws//dev/cu.xxx [--app-id ${DEFAULT_APP_ID}] [--channel alicia-teleop] [--topic teleop] [--speed 573] [--execute-frequency 50] [--no-wait-ok] [--recv-csv rtm_received.csv] [--send-csv m_commands.csv] [--chrome "${DEFAULT_CHROME_PATH}"] [--rtm-user-id m-subscriber] [--rtm-token <token>] [--headed] [--verbose]`);
    process.exit(values.help ? 0 : 1);
  }

  return {
    appId: values['app-id'],
    rtmUserId: values['rtm-user-id'],
    rtmToken: values['rtm-token'] || undefined,
    channel: values.channel,
    topic: values.topic,
    followerWs: values['follower-ws'],
    speed: Number(values.speed),
    executeFrequency: Number(values['execute-frequency']),
    noWaitOk: values['no-wait-ok'],
    recvCsv: values['recv-csv'],
    sendCsv: values['send-csv'],
    chrome: values.chrome,
    headed: values.headed,
    verbose: values.verbose,
  };
}

async function main() {
  const args = parseCli();
  const followerDeviceId = extractDeviceIdFromWsUrl(args.followerWs);
  const recvCsvPath = args.recvCsv;
  const sendCsvPath = args.sendCsv;

  fs.writeFileSync(
    recvCsvPath,
    'seq,recv_time_ms,sent_at_ms,device_id,leader_j1_deg,leader_j2_deg,leader_j3_deg,leader_j4_deg,leader_j5_deg,leader_j6_deg,leader_gripper\n',
  );
  fs.writeFileSync(
    sendCsvPath,
    'seq,send_time_ms,follower_j1_deg,follower_j2_deg,follower_j3_deg,follower_j4_deg,follower_j5_deg,follower_j6_deg,follower_gripper,speed\n',
  );

  log('Subscriber start');
  log(`Follower device: ${followerDeviceId}`);
  log(`RTM channel: ${args.channel}`);
  log(`RTM topic: ${args.topic}`);
  log(`Execute tick frequency: ${args.executeFrequency} Hz`);
  log(`Wait for movej.ok: ${args.noWaitOk ? 'no' : 'yes'}`);
  log(`Receive CSV: ${recvCsvPath}`);
  log(`Send CSV: ${sendCsvPath}`);

  await connectDeviceViaRest(args.followerWs, 'alicia_m');
  log('Follower backend registration OK');

  const hostServer = await createBrowserHostServer();

  const browser = await chromium.launch({
    executablePath: args.chrome,
    headless: !args.headed,
  });

  const shutdown = async (code) => {
    try {
      await browser.close();
      await hostServer.close();
    } finally {
      process.exit(code);
    }
  };

  process.on('SIGINT', () => {
    log('Subscriber stopping on SIGINT');
    void shutdown(130);
  });

  const page = await browser.newPage();
  page.on('console', (msg) => log(`[browser] ${msg.text()}`));
  page.on('pageerror', (error) => log(`[browser:error] ${error.stack || error.message}`));

  await page.exposeBinding('appendRecvCsv', async (_source, row) => {
    fs.appendFileSync(recvCsvPath, `${row}\n`);
  });
  await page.exposeBinding('appendSendCsv', async (_source, row) => {
    fs.appendFileSync(sendCsvPath, `${row}\n`);
  });

  await page.goto(hostServer.url);
  await page.addScriptTag({ path: resolveAgoraRtcScriptPath() });
  await page.addScriptTag({ path: resolveAgoraRtmScriptPath() });

  await page.evaluate(async (cfg) => {
    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const log = (...parts) => console.log(parts.join(' '));
    const jointSigns = [1.0, 1.0, -1.0, -1.0, 1.0, -1.0];

    const mapJoints = (leaderJointsDeg) => leaderJointsDeg.slice(0, 6).map((value, index) => value * jointSigns[index]);
    const clampGripper = (value) => Math.max(0, Math.min(1000, Number(value ?? 0)));

    class JsonWsClient {
      constructor(url, label) {
        this.url = url;
        this.label = label;
        this.queue = [];
        this.waiters = [];
        this.ws = null;
      }

      async connect() {
        this.ws = new WebSocket(this.url);
        this.ws.addEventListener('message', (event) => {
          const msg = JSON.parse(event.data);
          for (let i = 0; i < this.waiters.length; i += 1) {
            const waiter = this.waiters[i];
            if (!waiter.predicate || waiter.predicate(msg)) {
              this.waiters.splice(i, 1);
              clearTimeout(waiter.timer);
              waiter.resolve(msg);
              return;
            }
          }
          this.queue.push(msg);
        });

        await new Promise((resolve, reject) => {
          this.ws.addEventListener('open', () => resolve(), { once: true });
          this.ws.addEventListener('error', (event) => reject(event.error || new Error(`${this.label} websocket error`)), { once: true });
        });
      }

      async send(payload) {
        this.ws.send(JSON.stringify(payload));
      }

      async waitFor(predicate, timeoutMs = 5000) {
        for (let i = 0; i < this.queue.length; i += 1) {
          const msg = this.queue[i];
          if (!predicate || predicate(msg)) {
            this.queue.splice(i, 1);
            return msg;
          }
        }
        return new Promise((resolve, reject) => {
          const waiter = {
            predicate,
            resolve,
            reject,
            timer: setTimeout(() => {
              this.waiters = this.waiters.filter((item) => item !== waiter);
              reject(new Error(`${this.label} wait timeout after ${timeoutMs}ms`));
            }, timeoutMs),
          };
          this.waiters.push(waiter);
        });
      }
    }

    const followerWs = new JsonWsClient(cfg.followerWs, 'follower');
    await followerWs.connect();
    const hello = await followerWs.waitFor((msg) => msg.type === 'hello' || msg.type === 'error', 5000);
    if (hello.type === 'error') {
      throw new Error(`follower hello failed: ${JSON.stringify(hello)}`);
    }
    log(`Follower websocket connected: ${hello.device_id}`);

    const { RTM, VERSION, setParameter } = window.AgoraRTM;
    log(`Agora RTM SDK version: ${VERSION}`);
    try {
      setParameter('RTM2_ENABLED', 'true');
      log('RTM parameter set: RTM2_ENABLED=true');
    } catch (error) {
      log(`RTM setParameter failed: ${error?.message || error}`);
    }

    const rtm = new RTM(cfg.appId, cfg.rtmUserId, { logLevel: 'warn' });
    rtm.addEventListener('status', (event) => {
      log(`RTM status state=${event.state} reason=${event.reason}`);
    });
    rtm.addEventListener('tokenPrivilegeWillExpire', () => {
      log('RTM token will expire in ~30s');
    });

    await rtm.login(cfg.rtmToken ? { token: cfg.rtmToken } : {});
    let useStream = false;
    try {
      const streamChannel = rtm.createStreamChannel(cfg.channel);
      await streamChannel.join({ withPresence: false, withMetadata: false, withLock: false });
      await streamChannel.joinTopic(cfg.topic, { meta: '' });
      await streamChannel.subscribeTopic(cfg.topic, { users: [] });
      log(`RTM login+stream subscribe OK: ${cfg.rtmUserId}`);
      useStream = true;
    } catch (error) {
      log(`RTM stream unavailable, falling back to message channel: ${error?.message || error}`);
      await rtm.subscribe(cfg.channel, { withMessage: true, withPresence: false });
      log(`RTM login+subscribe OK: ${cfg.rtmUserId}`);
    }

    const executeQueue = [];
    let lastQueuedSeq = -1;
    let droppedFrames = 0;
    let executedSeq = -1;
    let lastVerboseAt = 0;
    let lastRecvLogAt = 0;
    const intervalMs = 1000 / cfg.executeFrequency;
    let nextTickAt = performance.now();
    const maxQueueSize = 2000;

    rtm.addEventListener('message', (event) => {
      if (event.channelName !== cfg.channel) {
        return;
      }
      const isStream = event.channelType === 'STREAM' || event.channelType === 2;
      const isMessage = event.channelType === 'MESSAGE' || event.channelType === 1;
      if (useStream) {
        if (!isStream || event.topicName !== cfg.topic) {
          return;
        }
      } else if (!isMessage) {
        return;
      }
      try {
        const payload = JSON.parse(typeof event.message === 'string' ? event.message : new TextDecoder().decode(event.message));
        if (payload.type !== 'leader.state') {
          return;
        }
        if (payload.seq <= lastQueuedSeq) {
          droppedFrames += 1;
          log(`Drop non-increasing seq=${payload.seq} lastQueuedSeq=${lastQueuedSeq}`);
          return;
        }
        const recvTimeMs = Date.now();
        if (cfg.verbose && recvTimeMs - lastRecvLogAt >= 1000) {
          lastRecvLogAt = recvTimeMs;
          log(`recv seq=${payload.seq} queued=${executeQueue.length} channelType=${event.channelType} topic=${event.topicName || ''}`);
        }
        payload.recv_time_ms = recvTimeMs;
        if (executeQueue.length >= maxQueueSize) {
          executeQueue.shift();
          droppedFrames += 1;
        }
        executeQueue.push(payload);
        lastQueuedSeq = payload.seq;
        window.appendRecvCsv([
          payload.seq,
          recvTimeMs,
          payload.sent_at_ms ?? '',
          payload.device_id ?? '',
          ...(payload.joints_deg || []).slice(0, 6),
          payload.gripper ?? '',
        ].join(','));
      } catch (error) {
        log(`RTM message parse error: ${error.message}`);
      }
    });

    for (;;) {
      const now = performance.now();
      if (now < nextTickAt) {
        await sleep(nextTickAt - now);
      }
      nextTickAt += intervalMs;

      if (executeQueue.length === 0) {
        if (performance.now() - nextTickAt > intervalMs * 2) {
          nextTickAt = performance.now();
        }
        continue;
      }

      const frame = executeQueue.shift();
      if (executedSeq >= 0 && frame.seq !== executedSeq + 1) {
        log(`Seq gap before execute: prev=${executedSeq} current=${frame.seq}`);
      }

      const followerCmd = {
        type: 'cmd.movej',
        joints_deg: mapJoints(frame.joints_deg || []),
        gripper: clampGripper(frame.gripper),
        speed: cfg.speed,
      };
      const sendTimeMs = Date.now();
      window.appendSendCsv([
        frame.seq,
        sendTimeMs,
        ...followerCmd.joints_deg,
        followerCmd.gripper,
        followerCmd.speed,
      ].join(','));

      await followerWs.send(followerCmd);
      if (!cfg.noWaitOk) {
        const reply = await followerWs.waitFor((msg) => msg.type === 'movej.ok' || msg.type === 'movej.error' || msg.type === 'error', 3000);
        if (reply.type !== 'movej.ok') {
          log(`Follower move error: ${JSON.stringify(reply)}`);
        }
      }

      executedSeq = frame.seq;
      if (cfg.verbose && Date.now() - lastVerboseAt >= 1000) {
        lastVerboseAt = Date.now();
        log(`executed seq=${executedSeq} queued=${executeQueue.length} dropped=${droppedFrames} joints=${JSON.stringify(followerCmd.joints_deg)} gripper=${Math.round(followerCmd.gripper)} speed=${cfg.speed}`);
      }

      if (performance.now() - nextTickAt > intervalMs * 2) {
        nextTickAt = performance.now();
        log(`Subscriber tick overrun; resync scheduler queue=${executeQueue.length} dropped=${droppedFrames}`);
      }
    }
  }, {
    appId: args.appId,
    rtmUserId: args.rtmUserId,
    rtmToken: args.rtmToken,
    channel: args.channel,
    topic: args.topic,
    followerWs: args.followerWs,
    speed: args.speed,
    executeFrequency: args.executeFrequency,
    noWaitOk: args.noWaitOk,
    verbose: args.verbose,
  });
}

main().catch((error) => {
  log(`Subscriber fatal: ${error.stack || error.message}`);
  process.exit(1);
});
