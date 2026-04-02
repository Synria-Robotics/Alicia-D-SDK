#!/usr/bin/env node

import { parseArgs } from 'node:util';
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
      'rtm-user-id': { type: 'string', default: `d-publisher-${Date.now()}` },
      'rtm-token': { type: 'string', default: process.env.AGORA_RTM_TOKEN ?? '' },
      'channel': { type: 'string', default: 'alicia-teleop' },
      'topic': { type: 'string', default: 'teleop' },
      'leader-ws': { type: 'string' },
      'frequency': { type: 'string', default: '50' },
      'send-frequency': { type: 'string', default: '50' },
      'chrome': { type: 'string', default: DEFAULT_CHROME_PATH },
      'headed': { type: 'boolean', default: false },
      'verbose': { type: 'boolean', default: false },
      'help': { type: 'boolean', short: 'h', default: false },
    },
    allowPositionals: false,
  });

  if (values.help || !values['leader-ws']) {
    console.log(`Usage:
  node publish_d_ws_to_rtm.js --leader-ws ws://localhost:8000/robots/ws//dev/cu.xxx [--app-id ${DEFAULT_APP_ID}] [--channel alicia-teleop] [--topic teleop] [--frequency 50] [--send-frequency 50] [--chrome "${DEFAULT_CHROME_PATH}"] [--rtm-user-id d-publisher] [--rtm-token <token>] [--headed] [--verbose]`);
    process.exit(values.help ? 0 : 1);
  }

  return {
    appId: values['app-id'],
    rtmUserId: values['rtm-user-id'],
    rtmToken: values['rtm-token'] || undefined,
    channel: values.channel,
    topic: values.topic,
    leaderWs: values['leader-ws'],
    frequency: Number(values.frequency),
    sendFrequency: Number(values['send-frequency']),
    chrome: values.chrome,
    headed: values.headed,
    verbose: values.verbose,
  };
}

async function main() {
  const args = parseCli();
  const leaderDeviceId = extractDeviceIdFromWsUrl(args.leaderWs);

  if (!(args.frequency > 0)) {
    throw new Error(`Invalid frequency: ${args.frequency}`);
  }
  if (!(args.sendFrequency > 0)) {
    throw new Error(`Invalid send frequency: ${args.sendFrequency}`);
  }

  log('Publisher start');
  log(`Leader device: ${leaderDeviceId}`);
  log(`RTM channel: ${args.channel}`);
  log(`RTM topic: ${args.topic}`);
  log(`Sample tick frequency: ${args.frequency} Hz`);
  log(`RTM max send frequency: ${args.sendFrequency} Hz`);
  if (args.frequency > 50) {
    log('Warning: for RTM teleop, >50 Hz usually has no practical benefit and increases timing pressure.');
  }

  await connectDeviceViaRest(args.leaderWs, 'alicia_d');
  log('Leader backend registration OK');

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
    log('Publisher stopping on SIGINT');
    void shutdown(130);
  });

  const page = await browser.newPage();
  page.on('console', (msg) => log(`[browser] ${msg.text()}`));
  page.on('pageerror', (error) => log(`[browser:error] ${error.stack || error.message}`));

  await page.goto(hostServer.url);
  await page.addScriptTag({ path: resolveAgoraRtcScriptPath() });
  await page.addScriptTag({ path: resolveAgoraRtmScriptPath() });

  await page.evaluate(async (cfg) => {
    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const log = (...parts) => console.log(parts.join(' '));

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

    const leaderWs = new JsonWsClient(cfg.leaderWs, 'leader');
    await leaderWs.connect();
    const hello = await leaderWs.waitFor((msg) => msg.type === 'hello' || msg.type === 'error', 5000);
    if (hello.type === 'error') {
      throw new Error(`leader hello failed: ${JSON.stringify(hello)}`);
    }
    log(`Leader websocket connected: ${hello.device_id}`);

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
    log(`RTM login OK: ${cfg.rtmUserId}`);

    let streamChannel = null;
    let useStream = false;
    try {
      streamChannel = rtm.createStreamChannel(cfg.channel);
      await streamChannel.join({ withPresence: false, withMetadata: false, withLock: false });
      await streamChannel.joinTopic(cfg.topic, { meta: '' });
      log(`RTM stream join OK: channel=${cfg.channel} topic=${cfg.topic}`);
      useStream = true;
    } catch (error) {
      log(`RTM stream unavailable, falling back to message channel: ${error?.message || error}`);
    }

    let seq = 0;
    let lastVerboseAt = 0;
    const intervalMs = 1000 / cfg.frequency;
    const sendIntervalMs = 1000 / cfg.sendFrequency;
    let nextSampleAt = performance.now();
    let nextSendAt = performance.now();
    const publishQueue = [];
    let droppedSamples = 0;
    let droppedSends = 0;
    const maxQueueSize = 2000;

    const samplerLoop = async () => {
      for (;;) {
        const now = performance.now();
        if (now < nextSampleAt) {
          await sleep(nextSampleAt - now);
        }
        nextSampleAt += intervalMs;

        const sampledAtMs = Date.now();
        await leaderWs.send({ type: 'get.state' });
        const leaderState = await leaderWs.waitFor((msg) => msg.type === 'state' || msg.type === 'state.error', 3000);

        if (leaderState.type === 'state.error') {
          log(`Leader state error: ${leaderState.msg || 'unknown'}`);
        } else {
          if (publishQueue.length >= maxQueueSize) {
            publishQueue.shift();
            droppedSamples += 1;
          }
          publishQueue.push({
            type: 'leader.state',
            seq,
            sampled_at_ms: sampledAtMs,
            source: 'alicia_d_ws',
            device_id: leaderState.device_id || cfg.leaderDeviceId,
            joints_deg: (leaderState.joints_deg || []).slice(0, 6),
            gripper: leaderState.gripper ?? 0,
            unit: leaderState.unit || 'deg',
          });
          seq += 1;
        }

        if (performance.now() - nextSampleAt > intervalMs * 2) {
          nextSampleAt = performance.now();
          log(`Publisher sample tick overrun; resync scheduler queue=${publishQueue.length} dropped=${droppedSamples}`);
        }
      }
    };

    const senderLoop = async () => {
      for (;;) {
        const now = performance.now();
        if (now < nextSendAt) {
          await sleep(nextSendAt - now);
        }
        nextSendAt += sendIntervalMs;

        if (publishQueue.length === 0) {
          if (performance.now() - nextSendAt > sendIntervalMs * 2) {
            nextSendAt = performance.now();
          }
          continue;
        }

        const payload = publishQueue.shift();
        payload.sent_at_ms = Date.now();
        try {
          if (useStream) {
            await streamChannel.publishTopicMessage(cfg.topic, JSON.stringify(payload), { customType: 'teleop.state' });
          } else {
            await rtm.publish(cfg.channel, JSON.stringify(payload), { channelType: 'MESSAGE', customType: 'teleop.state' });
          }
        } catch (error) {
          droppedSends += 1;
          const msg = error?.message || String(error);
          if (msg.includes('-10021') || msg.toLowerCase().includes('exceeds limitation')) {
            log(`RTM publish rate-limited; backing off. queue=${publishQueue.length} dropped=${droppedSends}`);
            nextSendAt = performance.now() + Math.max(sendIntervalMs, 100);
          } else {
            log(`RTM publish failed: ${msg}`);
          }
          continue;
        }

        if (cfg.verbose && payload.sent_at_ms - lastVerboseAt >= 1000) {
          lastVerboseAt = payload.sent_at_ms;
          log(`published seq=${payload.seq} queue=${publishQueue.length} dropped=${droppedSamples} send_dropped=${droppedSends} joints=${JSON.stringify(payload.joints_deg)} gripper=${Math.round(payload.gripper)}`);
        }
      }
    };

    await Promise.all([samplerLoop(), senderLoop()]);
  }, {
    appId: args.appId,
    rtmUserId: args.rtmUserId,
    rtmToken: args.rtmToken,
    channel: args.channel,
    topic: args.topic,
    leaderWs: args.leaderWs,
    leaderDeviceId,
    frequency: args.frequency,
    sendFrequency: args.sendFrequency,
    verbose: args.verbose,
  });
}

main().catch((error) => {
  log(`Publisher fatal: ${error.stack || error.message}`);
  process.exit(1);
});
