[TOC]

# Agora-RTE-Extension

## Introduction

Agora RTE Extension provides the ability for extension developer to interact with Agora RTC SDK NG's VideoTrack and
AudioTrack object, making video and audio processing possible.

By receiving `MediaStreamTrack` or `AudioNode` as input, running custom processing procedure such as `WASM` module
or `AudioWorkletNode`, and finally generating processed `MediaStreamTrack` or `AudioNode`, it will construct a media
processing pipeline to allow custom media processing provided by developers.

## How Extension and Processor Interacts With Agora RTC SDK NG

A `Processor` basically connects to other `Processor`s with `pipe` method:

```typescript
processorA.pipe(processorB);
```

The `pipe` method returns the `Processor` passed as parameter itself, making a function chaining style:

```typescript
//processor actually is processorB
const processor = processorA.pipe(processorB);

//function chaining 
processorA.pipe(processorB).pipe(processorC);
```

On AgoraRTC SDK NG v4.10.0 and afterwards, the `ILocalVideoTrack` and `ILocalAudioTrack` objects also have `pipe` method
on it:

```typescript
const localVideoTrack = AgoraRTC.createCameraVideoTrack();

localVideoTrack.pipe(videoProcessor);
```

To make the processed media rendering locally and transmitting through WebRTC, `processorDestination` property
on `ILocalVideoTrack` and `ILocalAudioTrack` has to be the final processor through the pipeline:

```typescript
localVideoTrack.pipe(videoProcessor).pipe(localVideoTrack.processorDestination);
```

----
An `Extension` receives injected utility functionality such as `logger` and `reporter`
during `AgoraRTC.registerExtensions` function call:

```typescript
AgoraRTC.registerExtensions([videoExtension, audioExtension]);
```

`Extension` also provides `createProcessor` method for constructing `Processor` instance:

```typescript
const videoProcessor = videoExtension.createProcessor();
```

----
Wrap it up:

```typescript
const videoExtension = new VideoExtension();
AgoraRTC.registerExtensions([videoExtension]);

const localVideoTrack = await AgoraRTC.createCameraVideoTrack();
const videoProcessor = videoExtension.createProcessor();

localVideoTrack.pipe(videoProcessor).pipe(localVideoTrack.processorDestination);
```

## Extension and Processor APIs for extension developers

### Extension

#### `Extension._createProcessor`

Abstract class `Extension` has one abstract method `_createProcessor` needs to be implemented:

```typescript
abstract class Extension<T extends BaseProcessor> {
  abstract _createProcessor(): T;
}
```

When implemented, it should return a `VideoProcessor` or `AudioProcessor` instance.

`AgoraRTC` developer calling `extension.createProcessor()` will return the processor returned by `_createProcessor`.

#### `Extension.setLogLevel`

Abstract class `Extension` has one static method `setLogLevel` :

```typescript
abstract class Extension<T extends BaseProcessor> {
  public static setLogLevel(level: number): void
}
```

`AgoraRTC` developer calling `Extension.setLogLevel(level)`  will set the output log level of the extension.

#### `Extension.checkCompatibility`

Abstract class `Extension` has one optional abstract public method `checkCompatibility` could be implemented:

```typescript
abstract class Extension<T extends BaseProcessor> {
  public abstract checkCompatibility?(): boolean;
}
```

When implemented, it should return a `boolean` value indicating whether extension could be run inside current browser environment.

### VideoProcessor

#### `VideoProcessor.name`

Abstract property `name` on `VideoProcessor` has to be implemented in order to name processor:

```typescript
abstract name: string;
```

#### `VideoProcessor.onPiped`

Abstract optional method `onPiped` could be implemented in order to be notified when processor connected to a pipeline
with `ILocalVideoTrack` as it's source:

```typescript
abstract onPiped?(context: IProcessorContext): void;
```

It will only be called when an `ILocalVideoTrack` object from `AgoraRTC` was connected to the pipeline, or when the
processor was connected to a pipeline with `ILocalVideoTrack` as its source.
> Pipeline without an `ILocalVideoTrack` as it's source, `onPiped` method will not be called for processors belonging to this pipeline until an `ILocalVideoTrack` connected to it.

```typescript
videoTrack.pipe(processor);//will be called

processorA.pipe(processorB);//will NOT be called
videoTrack.pipe(processorA);//will be called for both processorA and processorB
```

#### `VideoProcessor.onUnpiped`

Abstract optional method `onUnpiped` could be implemented in order to be notified when processor disconnected to a
pipeline:

```typescript
abstract onUnPiped?(): void;
```

#### `VideoProcessor.onTrack`

Abstract optional method `onTrack` could be implemented in order to be notified when the previous processor
or `ILocalVideoTrack` feeds output `MediaStreamTrack` to the current processor:

```typescript
abstract onTrack?(track: MediaStreamTrack, context: IProcessorContext): void;
```

#### `VideoProcessor.onEnableChange`
Abstract optional method `onEnableChange` could be implemented in order to be notified when processor's `_enabled`
property has changed:
```typescript
abstract onEnableChange?(enabled: boolean): void | Promise<void>;
```
`AgoraRTC` developer calling `processor.enable()` and `processor.disable()` may change `_enabled` property and consequently calling `onEnableChange`, but enabling an already enabled processor or disabling an already disabled processor will not.
#### `VideoProcessor._enabled`
property `_enabled` describes enabled status of the current processor.

```typescript
protected _enabled :boolean = true;
```

It defaults to `true` ,  but could be change inside processor constructor:

```typescript
class CustomProcessor extends VideoProcessor {
  public constructor(){
    this._enabled = false;
  }
}
```

Other than that, it should not be modified directly.

#### `VideoProcessor.enabled`

Getter `enabled` describes enabled status of the current processor.

```typescript
public get enabled(): boolean;
```

#### `VideoProcessor.inputTrack`

Optional property `inputTrack` will be setted when the previous processor or `ILocalVideoTrack` feeds output track on the current processor:

```typescript
protected inputTrack?:MediaStreamTrack;
```

#### `VideoProcessor.outputTrack`

Optional property `outputTrack` will be setted when the current processor calling `output()`  to generate output `MediaStreamTrack`:

```typescript
protected outputTrack?:MediaStreamTrack;
```

#### `VideoProcessor.ID`

Readonly property `ID` is a random ID for the current processor instance:

```typescript
public readonly ID:string;
```

#### `VideoProcessor.kind`

Getter `kind` describes current processor's kind, which is either `audio` or `video`:

```typescript
public get Kind():'video' | 'audio';
```

#### `VideoProcessor.context`

Optional property `context` is the current processor's `IProcessorContext` :

```typescript
protected context?: IProcessorContext;
```

#### `VideoProcessor.output`
method `output` should be called when processor was about to generate processed `MediaStreamTrack`:
```typescript
output(track: MediaStreamTrack, context: IProcessorContext): void;
```


### AudioProcessor

`AudioProcessor` shares almost all the property/methods with `VideoProcessor`, with 1 exception that `AudioProcessor`'s processorContext is `IAudioProcessorContext`; and with several additions:

#### `AudioProcessor.onNode`

Abstract optional method `onNode` could be implemented in order to be notified when the previous processor
or `ILocalAudioTrack` feeds output `AudioNode` to the current audio processor:

```typescript
abstract onNode?(node: AudioNode, context: IAudioProcessorContext): void;
```

#### `AudioProcessor.output`

method `output` should be called when audio processor was about to generate processed `MediaStreamTrack` or `AudioNode`:

```typescript
output(track: MediaStreamTrack | AudioNode, context: IProcessorContext): void;
```

#### `AudioProcessor.inputNode`

Optional property `inputNode` will be setted when the previous processor or `ILocalAudioTrack` feeds output audio node on the current processor:

```typescript
protected inputNode?:AudioNode;
```

####`AudioProcessor.outputNode`

Optional property `outputNode` will be setted when the current processor calling `output()`  to generate output `AudioNode`:

```typescript
protected outputNode?:AudioNode;
```

### ProcessorContext

`ProcessorContext` provides the ability to interact with the process pipeline's source which is `ILocalVideoTrack` or `ILocalAudioTrack`, and possiblly affecting media capture.

`ProcessorContext` will be assgined to the processor once the processor was connected with a pipeline has `ILocalVideoTrack` or `ILocalAudioTrack` as it's source.

#### `ProcessorContext.requestApplyConstraints`

Method `requestApplyConstraints` provides the ability to change the `MediaTrackConstraints` used for getting pipeline source's `MediaStreamTrack` :

```typescript
public requestApplyConstraints(constraints: MediaTrackConstraints, processor: IVideoProcessor): Promise<void>;
```

Constraints supplied in `requestApplyConstraints` will be merged with the original constraints used for creating `ICameraVideoTrack`. If several processors inside the same pipline all request to apply additional constraints, the pipe order will be considered to make the final constraints.

#### `ProcessorContext.requestRevertConstraints`

Method`requestRevertConstraints` provides the ability to revert previous constraints request using `requestApplyConstraints`:

```typescript
public requestRevertConstraints(processor: IVideoProcessor):void;
```
### AudioProcessorContext
`AudioProceesorContext` inherits all the methods provided by `ProcessorContext`, with one addition `getAudioContext`.
#### `getAudioContext`
Method `getAudioContext` provides the ability to get `AudioContext` object of the current pipeline:
```typescript
public getAudioContext(): AudioContext;
```
### Ticker
`Ticker` is a utitly class that helps with periodic tasks.

`Ticker` provides simple interface for choosing periodic task implementation, add/remove task and start/stop task.

#### `new Ticker`

`Ticker` constructor requires ticker type and tick interval as parameter:

```typescript
class Ticker{
  public constructor(type:"Timer" | "RAF" | "Oscillator", interval: number):Ticker; 
}
```

`Ticker` has three implementation to choose from:

- `Timer`: uses `setTimeout` as the internal timer
- `RAF`: uses `requestAnimationFrame` as the internal timer. Most users should choose this type of `Ticker` as it provides best rendering performance
- `Osciilator`: uses `WebAudio`'s `OscillatorNode` as the internal timer. Can still keep running even the browser tab is not focused.

`interval` sets the time between the next callback. It is a best effort timing not an exactly timing.

#### `Ticker.add`

`Ticker.add` adds a task to the ticker:

```typescript
public add(fn: Function): void;
```

#### `Ticker.remove`

`Ticker.remove` removes the task added to the ticker previously:

```typescript
public remove():void;
```

#### `Ticker.start`

`Ticker.start` starts the already add task with settled ticker type and interval:

```typescript
public start():void;
```

####`Ticker.stop`

`Ticker.stop` stops the previously add task:

```typescript
public stop():void;
```

### Logger

`Logger` is a global utility singleton that helps the logging. It provides four log levels to log to the console.

When the extension was registered with `AgoraRTC.registerExtension`, and the `AgoraRTC` developer choose to upload log, extension logs loged with `Logger` will also been uploaded.

#### `Logger.info`, `Logger.debug`, `Logger.warning`, `Logger.error`

Theses methods log with different level:

```typescript
public info(...args:any[]):void;
public debug(...args:any[]):void;
public warning(...args:any[]):void;
public error(...args:any[]):void;
```

#### `Logger.setLogLevel`

`Logger.setLogLevel` set the output log level of the extension.

```typescript
public setLogLevel(level: number): void;
```

### Reporter

`Reporter` is a global utility singleton that helps with event reporting to Agora analysis platform:

#### `Reporter.reportApiInvoke`

`Repoter.reportApiInvoke` can report public API calling event to Agora analysis platform:

```typescript
interface ReportApiInvokeParams {
  name: string;
  options: any;
  reportResult?: boolean;
  timeout?: number;
}
interface AgoraApiExecutor<T> {
  onSuccess: (result: T) => void;
  onError: (err: Error) => void;
}

public reportApiInvoke<T>(params: ReportApiInvokeParams): AgoraApiExecutor<T>;
```

It accepts `ReportAPIInvokeParams` as parameter:

- `ReportAPIInvokeParams.name`: the name of the public API
- `options`: the arguments, or any other options related to this API invoke
- `reportResult`: whether to report API invoke result
- `timeout`: specifies how long it is `Reporter` thinks the API calling is timeout.

It reports two callback methods, `onSuccess` and `onEror`, which can be called when the API calling success or failed accordingly.

## Extending Extension
Extending an `Extension` is fairly straightforward as we only need to implement `_createProcessor` abstract method:

```typescript
import {Extension} from 'agora-rte-extension'

class YourExtension extends Extension<YourProcessor> {
  protected _createProcessor(): YourProcessor {
    return new YourProcessor(); 
  }
}
```

## Extending Processor

There are several abstract methods could be implemented and they will be called at the different timing of the processing pipeline.

### `onTrack` and `onNode`

`onTrack` and `onNode` method will be called when the previous processor/LocalTrack generated output. They are the main entry point for us to process media:

```typescript
class CustomVideoProcessor extends VideoProcesor {
  protected onTrack(track: MediaStreamTrack, context: IProcessorContext){}
}

class CustomAudioProcessor extends AudioProcessor {
  protected onNode(node: AudioNode, context: IAudioProcessorContext){} 
}
```

### Video Processing

Typically, doing video processing requests extracting each video frame as `ImageData` or `ArrayBuffer`.

As for now `InsertableStream` have not been globally supported by browser vendors yet, we  use `canvas` API here to extract video frame data:

```typescript
class CustomVideoProcessor extends VideoProcessor {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private videoElement:HTMLVideoElement;
 
  constructor(){
    super();
    
   	//initialize canvas element
    this.canvas = document.createElement('canvas');
    this.canvas.width = 640;  // canvas's width and height will be your output video streams video dimension 
    this.canvas.height = 480;
    this.ctx = this.canvas.getContext('2d')!;
    
    //initialize video element
    this.videoElement = document.createElement('video');
    this.videoElement.muted = true;
  }
  
  onTrack(track:MediaStreamTrack, context: IProcessorContext){
    //loding MediaStreamTrack into HTMLVideoElement
    this.videoElement.srcObject = new MediaStream([track]);
    this.videoElement.play();
    
    //extract ImageData
    this.ctx.drawImage(this.videoElement, 0, 0);
    const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
  }
}
```

As we can see here video frame data was only been eatracted once inside the `onTrack` method, but we need to run it inside a constant loop to ouput constant frame rate.  Luckily, we can leverage `requestAnimationFrame`to do this for us:

```typescript
class CustomVideoProcessor extends VideoProcessor {
  onTrack(track:MediaStreamTrack, context: IProcessorContext){
    this.videoElement.srcObject = new MediaStream([track]);
    this.videoElement.play();
    
    this.loop();
  }
  
  loop(){
    this.ctx.drawImage(this.videoElement, 0, 0);
    const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
    
    this.process(imageData);
    
    requestAnimationFrame(()=>this.loop());
  }
  
  process(){
    //your custom video processing logic
  }
}
```
### Generating Video Processing Output

When we've done video processing, `Processor`'s `output` method should be used to generate video putput. `output` methods requires `MediaStreamTrack` and `IProcessorContext` as it's parameter, so we will need to assemble video buffer into a `MediaStreamTrack`.

Usually `canvas`'s `captureStream` helps us with it:

```typescript
class CustomVideoProcessor extends VideoProcessor {
  doneProcessing(){
    // making an MediaStream from canvas and get MediaStreamTrack
    const msStream = this.canvas.captureStream(30);
    const outputTrack = msStream.getVideoTracks()[0];
    
    //output processed track
    if(this.context){
      this.output(outputTrack, this.context);
    }
  }
}
```

### Audio Processing
Audio processing differs with video processing as that audio processing typically requires `WebAudio`'s capability to do custom audio processing.

We can implement `onNode` method to receive notification when the previous audio processor/`ILocalAudioTrack` generated output AudioNode:

```typescript
class CustomAudioProcessor extends AudioProcessor {
  onNode(node: AudioNode, context: IAudioProcessorContext) {}
}
```
We can call `IAudioProcessorContext.getAudioContext` to get `AudioContext` to create our own audioNode:
```typescript
class CustomAudioProcessor extends AudioProcessor {
  onNode(node: AudioNode, context: IAudioProcessorContext) {
    //accuire AudioContext
    const audioContext = context.getAudioContext();
    
    //create custom gaiNode
    const gainNode = audioContext.createGain();
  }
}
```
Also don't forget to connect the input audio node to our custom audio node:
```typescript
class CustomAudioProcessor extends AudioProcessor {
  onNode(node: AudioNode, context: IAudioProcessorContext) {
    const audioContext = context.getAudioContext();

    const gainNode = audioContext.createGain();
    
    //connect
    node.connect(gainNode);
  }
}
```
### Generating Audio Processing Output
When we've done audio processing, Processor's `output` method should be used to generate audio output. `output` methods requires `MediaStreamTrack`/`AudioNode` and `IAudioProcessorContext` as its parameter:
```typescript

class CustomAudioProcessor extends AudioProcessor {
  onNode(node: AudioNode, context: IAudioProcessorContext) {
    const audioContext = context.getAudioContext();

    const gainNode = audioContext.createGain();

    node.connect(gainNode);
    
    //output
    this.output(gainNode, context);
  }
}
```
## Testing
WIP
## Best Practices

### Audio Graph Connecting

### Handling Enable and Disable

### Error Handling

