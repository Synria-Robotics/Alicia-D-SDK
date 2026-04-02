#!/usr/bin/env node

import fs from 'node:fs';
import { parseArgs } from 'node:util';

const JOINT_SIGNS = [1.0, 1.0, -1.0, -1.0, 1.0, -1.0];

function usage() {
  console.log(`Usage:
  node compare_csv.js --recv rtm_received.csv --send m_commands.csv`);
}

function parseCli() {
  const { values } = parseArgs({
    options: {
      recv: { type: 'string' },
      send: { type: 'string' },
      help: { type: 'boolean', short: 'h', default: false },
    },
  });

  if (values.help || !values.recv || !values.send) {
    usage();
    process.exit(values.help ? 0 : 1);
  }

  return {
    recv: values.recv,
    send: values.send,
  };
}

function readCsv(file) {
  const text = fs.readFileSync(file, 'utf8').trim();
  const lines = text ? text.split('\n') : [];
  if (lines.length === 0) {
    return [];
  }
  const header = lines[0].split(',');
  return lines.slice(1).filter(Boolean).map((line) => {
    const cols = line.split(',');
    const row = {};
    for (let i = 0; i < header.length; i += 1) {
      row[header[i]] = cols[i] ?? '';
    }
    return row;
  });
}

function toNumber(value) {
  return value === '' || value === undefined ? NaN : Number(value);
}

function percentile(sorted, p) {
  if (sorted.length === 0) {
    return NaN;
  }
  const index = Math.min(sorted.length - 1, Math.max(0, Math.round((sorted.length - 1) * p)));
  return sorted[index];
}

function mean(values) {
  if (values.length === 0) {
    return NaN;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function fmt(value, digits = 3) {
  return Number.isFinite(value) ? value.toFixed(digits) : 'n/a';
}

function main() {
  const args = parseCli();
  const recvRows = readCsv(args.recv);
  const sendRows = readCsv(args.send);

  const recvBySeq = new Map(recvRows.map((row) => [Number(row.seq), row]));
  const sendBySeq = new Map(sendRows.map((row) => [Number(row.seq), row]));
  const matchedSeqs = [...recvBySeq.keys()].filter((seq) => sendBySeq.has(seq)).sort((a, b) => a - b);
  const recvOnlySeqs = [...recvBySeq.keys()].filter((seq) => !sendBySeq.has(seq)).sort((a, b) => a - b);
  const sendOnlySeqs = [...sendBySeq.keys()].filter((seq) => !recvBySeq.has(seq)).sort((a, b) => a - b);

  const delays = [];
  const jointAbsDiffs = [[], [], [], [], [], []];
  const gripperAbsDiffs = [];
  const mismatchSamples = [];

  for (const seq of matchedSeqs) {
    const recv = recvBySeq.get(seq);
    const send = sendBySeq.get(seq);
    const recvTime = toNumber(recv.recv_time_ms);
    const sendTime = toNumber(send.send_time_ms);
    if (Number.isFinite(recvTime) && Number.isFinite(sendTime)) {
      delays.push(sendTime - recvTime);
    }

    const expectedJoints = JOINT_SIGNS.map((sign, index) => sign * toNumber(recv[`leader_j${index + 1}_deg`]));
    const actualJoints = JOINT_SIGNS.map((_sign, index) => toNumber(send[`follower_j${index + 1}_deg`]));
    const jointDiffs = expectedJoints.map((value, index) => actualJoints[index] - value);
    jointDiffs.forEach((diff, index) => {
      if (Number.isFinite(diff)) {
        jointAbsDiffs[index].push(Math.abs(diff));
      }
    });

    const expectedGripper = Math.max(0, Math.min(1000, toNumber(recv.leader_gripper)));
    const actualGripper = toNumber(send.follower_gripper);
    if (Number.isFinite(expectedGripper) && Number.isFinite(actualGripper)) {
      gripperAbsDiffs.push(Math.abs(actualGripper - expectedGripper));
    }

    if (
      mismatchSamples.length < 10 &&
      (jointDiffs.some((diff) => Number.isFinite(diff) && Math.abs(diff) > 1e-9) ||
        (Number.isFinite(expectedGripper) && Number.isFinite(actualGripper) && Math.abs(actualGripper - expectedGripper) > 1e-9))
    ) {
      mismatchSamples.push({
        seq,
        jointDiffs,
        gripperDiff: actualGripper - expectedGripper,
      });
    }
  }

  const sortedDelays = [...delays].sort((a, b) => a - b);
  console.log(`recv rows: ${recvRows.length}`);
  console.log(`send rows: ${sendRows.length}`);
  console.log(`matched seq: ${matchedSeqs.length}`);
  console.log(`recv-only seq: ${recvOnlySeqs.length}`);
  console.log(`send-only seq: ${sendOnlySeqs.length}`);
  if (matchedSeqs.length > 0) {
    console.log(`seq range: ${matchedSeqs[0]} -> ${matchedSeqs[matchedSeqs.length - 1]}`);
  }
  console.log('');
  console.log('delay_ms');
  console.log(`  min=${fmt(sortedDelays[0])} avg=${fmt(mean(sortedDelays))} p50=${fmt(percentile(sortedDelays, 0.5))} p95=${fmt(percentile(sortedDelays, 0.95))} max=${fmt(sortedDelays[sortedDelays.length - 1])}`);
  console.log('');
  console.log('joint_abs_diff_deg');
  jointAbsDiffs.forEach((values, index) => {
    const sorted = [...values].sort((a, b) => a - b);
    console.log(`  j${index + 1}: max=${fmt(sorted[sorted.length - 1])} avg=${fmt(mean(sorted))}`);
  });
  const sortedGripper = [...gripperAbsDiffs].sort((a, b) => a - b);
  console.log(`  gripper: max=${fmt(sortedGripper[sortedGripper.length - 1])} avg=${fmt(mean(sortedGripper))}`);

  if (recvOnlySeqs.length > 0) {
    console.log('');
    console.log(`recv-only sample: ${recvOnlySeqs.slice(0, 10).join(', ')}`);
  }
  if (sendOnlySeqs.length > 0) {
    console.log('');
    console.log(`send-only sample: ${sendOnlySeqs.slice(0, 10).join(', ')}`);
  }
  if (mismatchSamples.length > 0) {
    console.log('');
    console.log('mismatch samples');
    for (const sample of mismatchSamples) {
      console.log(`  seq=${sample.seq} jointDiffs=${sample.jointDiffs.map((v) => fmt(v)).join('/')} gripperDiff=${fmt(sample.gripperDiff)}`);
    }
  }
}

main();
