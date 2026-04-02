<!-- Only for China -->
# Real-time Message SDK for JavaScript

## Table of contents

---

1. [Introduction](#Introduction)

2. [Requirements](#Requirements)

3. [Getting started](#Getting-started)

4. [Sending your first message](#Sending-your-first-message)

5. [Additional information](#Additional-information)

### Important Notice

> RTM javaScript SDK has been iterated to version 2.X, which will provide richer functions, better performance and better user experience. We hope that both new and returning users will be able to migrate to the new version to take advantage of its amazing new features.

## <a name="Introduction"></a>Introduction

---

The RTM SDK for javaScript allows you to easily add real-time interactions to client applications. RTM provides feature-rich, scalable, and proven real-time  engagement solutions trusted by companies like Glance, Poshmark, Litmatch, 米哈游(miHoyo), and 小天才(Imoo), etc.

RTM has been widely used by 3000+ customers in dozens of application scenarios such as conference control, interactive games, metaverse, online education, e-commerce retail, smart devices, etc.

### How it works

The RTM SDK provides complete functionality to provide a rich real-time interactive experience by instantiating an RTM instance, logging in, subscribing to a channel, implementing event listeners to receive messages and other events, and the ability to send messages. Once this basic function is in place, congratulations, you can now interact with anyone in the world online in real time!

Once you've done this, take a look at [all the other features](https://doc.shengwang.cn/doc/rtm2/javascript/landing-page) RTM supports and add the ones that work best for your users.

### Documentation

Find out more about RTM SDK for JavaScript in [the documentation](https://doc.shengwang.cn/doc/rtm2/javascript/landing-page). If you have any comments, questions or feature requests, let us know by sending email to rtm-support@agora.io.

## <a name="Requirements"></a>Requirements

---

This section shows you the prerequisites you need to check for using RTM SDK for JavaScript.

### Supported browsers

| Browser                | Supported versions          |
| :--------------------: | --------------------------- |
| Chrome macOS           | 90.0 or higher              |
| Chrome Linux           |  93.0 or higher             |
| Chrome Windows         |  90.0 or higher             |
| Firefox macOS          |  85.0 or higher             |
| Firefox Windows        |  85.0 (x64) or higher       |
| Microsoft Edge macOS   |  114.0.1823.41 or higher    |
| Microsoft Edge Windows |  113.0.1774.57 or higher    |
| Safari macOS           |  15.6.1 or higher           |

## <a name="Getting-started"></a>Getting started

---

### Step 1: Create a Agora Project from your console

Before installing RTM SDK, you need to create an Agora project on the [console](https://console.shengwang.cn/). You will need the `App ID` of your RTM application when initializing the RTM SDK. In order to quickly experience the features, please select debug mode in the authentication mechanism column when creating the project.

> **Note**: Your application  built with different `App ID` do not communicate with each other. To send and receive messages between different apps, you need to make sure you use the same `App ID`.

### Step 2 : Install the RTM SDK

You can obtain the latest RTM JavaScript SDK through any of the following methods.

#### npm

```bash
npm install agora-rtm
```

> Note: To use npm to install the RTM SDK, Node.js must be first installed on your system.

#### CDN

[Click here](https://doc.shengwang.cn/doc/rtm2/homepage#sdk-) download the latest version of the JavaScript SDK and add the following code to your project to reference it:

```bash
<script src="your_path_to_sdk/agora-rtm.x.y.z.min.js"></script>
```

> Replace x.y.z with the specific SDK version number, such as 2.1.4

### Step 3: Import the RTM SDK

```javascript
import AgoraRTM from 'agora-rtm';
```

If you are using TypeScript and have trouble importing Sendbird, please check your `tsconfig.json` file and change the value of `allowSyntheticDefaultImports` to true in `compilerOptions`.

## <a name="Sending-your-first-message"></a>Sending your first message

---

Now that the RTM SDK has been imported, we're ready to start sending a message.

### Step 4: Initialize the RTM client instance

In order to use the features of the RTM SDK, you should initiate the `RTM` instance at first:

```javascript
import AgoraRTM from 'agora-rtm';

const { RTM } = AgoraRTM;
// Fill in the App ID of your project.
const appId = "your_appId";
// Fill in your user ID.
const userId = "your_userId";
const msChannelName = "Chat_room";

try {
  const rtm = new RTM(appId, userId);
} catch (status) {
  console.log("Error");
  console.log(status);
}
```

You need to replace "your_appId" and "your_userId" in the code with your project's App ID and your user ID.

### Step 5: Add event listener

The event listener helps you implement the processing logic after the messages and events received in the channel. Add the following code to your program to display the received messages or event notifications:

```javascript
// Paste the following code snippet below "Add the event listener" comment
// Message event handler.
rtm.addEventListener("message", event => {
  showMessage(event.publisher, event.message);
});
// Presence event handler.
rtm.addEventListener("presence", event => {
  if (event.eventType === "SNAPSHOT") {
    showMessage("INFO", "I Join");
  }
  else {
    showMessage("INFO", event.publisher + " is " + event.type);
  }
});
// Connection state changed event handler.
rtm.addEventListener("status", event => {
  // The current connection state.
  const currentState = event.state;
  // The reason why the connection state changes.
  const changeReason = event.reason;
  showMessage("INFO", JSON.stringify(event));
});
```

### Step 6: Login to RTM server

Once the SDK is initialized, your client app can then login to the RTM server. If you attempt to call a RTM SDK method without login, an `RTM_ERROR_NOT_LOGIN (-10002)` error would return.

```javascript
// Paste the following code snippet below "Log in the RTM server." comment
try {
  const result = await rtm.login({ token: 'your-token'});
  console.log(result);
} catch (status) {
  console.log(status);
}
```

### Step 7：Send and receive messages

After calling the publish method to send a message to the Message Channel, RTM will distribute the message to all subscribers of the channel. The following code demonstrates how to send a string type message. Add this code snippet to the program:

> You need to string serialize the message payload before calling the publish method to send the message.

```javascript
try {
  const result = await rtm.publish(msChannelName, message);
  console.log(result);
} catch (status) {
  console.log(status);
}
```

Call the subscribe method to subscribe to this channel to receive messages in this channel. Add the following code to your program:

```javascript
try {
  const result = await rtm.subscribe(msChannelName);
  console.log(result);
} catch (status) {
  console.log(status);
}
```

## <a name="Additional-information"></a>Additional information

---

Now, you have learned how to use the RTM JavaScript SDK to send and receive messages. Next, you can learn how to use more functions through the SDK's [API reference](https://doc.shengwang.cn/api-ref/rtm2/javascript/toc-configuration/configuration).

If you have any comments, questions or feature requests, let us know by sending email to rtm-support@agora.io.
