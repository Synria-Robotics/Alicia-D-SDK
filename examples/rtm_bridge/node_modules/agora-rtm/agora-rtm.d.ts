import EventEmitter from 'events';
import { IDebugger } from 'debug';
import { ConnectionState, ConnectionDisconnectedReason } from 'agora-rtc-sdk-ng';

/** @zh-cn
 * 连接状态改变原因
 */
/**
 * Reasons for a connection state change.
 */
type RTMConnectionChangeReason = 'CONNECTING'
/** @zh-cn
 * SDK 登录 Agora RTM 系统成功。
 */
/**
 * The SDK has logged in the Agora RTM system.
 */
 | 'LOGIN_SUCCESS'
/** @zh-cn
 * SDK 登录 Agora RTM 系统失败。
 */
/**
 * The SDK fails to log in the Agora RTM system, because, for example, the token has expired.
 */
 | 'REJECTED_BY_SERVER'
/** @zh-cn
 * SDK 无法登录 Agora RTM 系统超过 6 秒，停止登录。
 */
/**
 * The login has timed out, and the SDK stops logging in. The current login timeout is set as six seconds.
 */
 | 'LOST'
/** @zh-cn
 * SDK 与 Agora RTM 系统的连接被中断超过 4 秒。
 */
/**
 * The connection between the SDK and the Agora RTM system is interrupted for more than four seconds.
 */
 | 'INTERRUPTED'
/** @zh-cn
 * SDK 已登出 Agora RTM 系统。
 */
/**
 * The SDK has logged out of the Agora RTM system.
 */
 | 'LOGOUT'
/** @zh-cn
 * SDK 被服务器禁止登录 Agora RTM 系统。
 */
/**
 * Login is banned by the Agora RTM server.
 */
 | 'KICKED_OUT_BY_SERVER'
/** @zh-cn
 * 另一个用户正以相同的 uid 登陆 Agora RTM 系统。
 */
/**
 * Another instance has logged in the Agora RTM system with the same uid.
 */
 | 'SAME_UID_LOGIN'
/** @zh-cn
 * 用户使用的token已过期。
 */
/**
 * The token used by the user has expired.
 */
 | 'TOKEN_EXPIRED'
/**
 * @zh-cn
 * 服务暂不可用。
 */
/**】
 * The presence server not ready.
 */
 | 'PRESENCE_NOT_READY';
/** @zh-cn
 * SDK 与 Agora RTM 系统的连接状态类型
 */
/**
 * Connection states between the SDK and the Agora RTM system.
 */
type RTMConnectionState = 
/** @zh-cn
 * 初始状态。SDK 未连接到 Agora RTM 系统。
 *
 * App 调用方法 {@link RTMClient.login} 时，SDK 开始登录 Agora RTM 系统，触发回调 {@link RTMEvents.status}，并切换到 {@link CONNECTING} 状态。
 *
 */
/**
 * When the app calls the {@link RTMClient.login} method, the SDK logs in the Agora RTM system, triggers the {@link RTMEvents.status} callback, and switches to the {@link CONNECTING} state.
 */
'DISCONNECTED'
/** @zh-cn
 * SDK 正在登录 Agora RTM 系统。
 *
 * - 方法调用成功时，SDK 会触发回调 {@link RTMEvents.status}，并切换到 {@link CONNECTED} 状态。</li>
 * - 法调用失败，SDK 会触发回调 {@link RTMEvents.status}，并切换到 {@link DISCONNECTED} 状态。</li>
 *
 */
/**
 * The SDK has logged in the Agora RTM system.
 * <ul>
 *     <li>Success = the SDK triggers the {@link RTMEvents.status} callback and switches to the {@link CONNECTED} state.</li,
 *     <li>Failure = the SDK triggers the {@link RTMEvents.status} callback and switches to the {@link DISCONNECTED} state.</li,
 * </ul>
 */
 | 'CONNECTING'
/** @zh-cn
 * SDK 已登录 Agora RTM 系统。
 * <ul>
 *     <li>如果 SDK 与 Agora RTM 系统的连接由于网络问题中断，SDK 会触发回调 {@link RTMEvents.status}，并切换到 {@link RECONNECTING} 状态。</li>
 *     <li>如果 SDK 因为相同 ID 已在其他实例或设备中登录等原因被服务器禁止登录，会触发回调 {@link RTMEvents.status}，并切换到 {@link FAILED} 状态。</li>
 *     <li>如果 App 调用方法 {@link RTMClient.logout}，SDK 登出 Agora RTM 系统成功，会触发回调 {@link RTMEvents.status}，并切换到 {@link DISCONNECTED} 状态。</li>
 * </ul>
 */
/**
 * The SDK has logged in the Agora RTM system.
 * <ul>
 *     <li>If the connection between the SDK and the Agora RTM system is interrupted because of network issues, the SDK triggers the {@link RTMEvents.status} callback and switches to the {@link RECONNECTING} state.</li>
 *     <li>If the login is banned by the server, for example, another instance has logged in with the same uid from a different device, the SDK triggers the {@link RTMEvents.status} callback and switches to the {@link FAILED} state.</li>
 *     <li>If the app calls the {@link RTMClient.logout} method and the SDK successfully logs out of the Agora RTM system, the SDK triggers the {@link RTMEvents.status} callback and switches to the {@link DISCONNECTED} state.</li>
 * </ul>
 */
 | 'RECONNECTING'
/** @zh-cn
 * SDK 正在重新登录 Agora RTM 系统。
 *
 * <ul>
 *     <li>如果 SDK 重新登录 Agora RTM 系统成功，会触发回调 {@link RTMEvents.status}，并切换到 {@link CONNECTED} 状态。</li>
 *     <li>如果 SDK 重新登录 Agora RTM 系统失败，会保持  {@link RECONNECTING} 状态。</li>
 *     <li>如果登录被服务器拒绝，SDK 会触发回调 {@link RTMEvents.status}，并切换到 {@link FAILED} 状态。</li>
 * </ul>
 *
 */
/**
 * The SDK keeps logging in the Agora RTM system.
 * <ul>
 *     <li>If the SDK successfully logs in the Agora RTM system again, it triggers the {@link  RTMEvents.status} callback and switches to the {@link CONNECTED} state.</li>
 *     <li>If the SDK fails to log in the Agora RTM system again, the SDK stays in the {@link RECONNECTING} state. </li>
 *     <li>If the login is rejected by the server, the SDK triggers the {@link  RTMEvents.status} callback and switches to the {@link FAILED} state.</li>
 * </ul>
 */
 | 'CONNECTED'
/** @zh-cn
 * SDK 停止登录 Agora RTM 系统。
 *
 * <p>原因可能为：</p>
 * <p><ul>
 * <li>另一实例已经以同一用户 ID 登录 Agora RTM 系统。</li>
 * <li>token 已过期。</li></ul></p>
 * 请在调用方法 {@link RTMClient.logout} 后，调用方法 {@link RTMClient.login} 登录 Agora RTM 系统。</p>
 */
/**
 * The SDK gives up logging in the Agora RTM system, possibly because another instance has logged in the Agora RTM system with the same uid.
 *
 * <p>Call the {@link RTMClient.logout} method before calling the {@link RTMClient.login} method to log in the Agora RTM system again.</p>
 */
 | 'FAILED';
/** @zh-cn
 * 消息类型。
 */
/**
 * Message types.
 */
declare enum MessageType {
    /** @zh-cn
     * 文本消息。
     */
    /**
     * A strig message.
     */
    STRING = "STRING",
    /** @zh-cn
     * 自定义二进制消息。
     */
    /**
     * A binary message.
     */
    BINARY = "BINARY"
}
/** @ignore */
declare enum LegacyAreaCode {
    /** @zh-cn
     * 中国大陆。
     */
    /**
     * Mainland China.
     */
    CN = "CN",
    /** @zh-cn
     * 北美区域。
     */
    /**
     * North America.
     */
    NA = "NA",
    /** @zh-cn
     * 欧洲区域。
     */
    /**
     * Europe.
     */
    EU = "EU",
    /** @zh-cn
     * 除中国大陆以外的亚洲区域。
     */
    /**
     * Asia excluding mainland China.
     */
    AS = "AS",
    /** @japan
     * 日本。
     */
    /**
     * Japan.
     */
    JP = "JP",
    /** @india
     * 印度。
     */
    /**
     * India.
     */
    IN = "IN",
    /** @global
     * （默认）全球。
     */
    /**
     * (Default) Global.
     */
    GLOB = "GLOB",
    /** @Oceania
     * 大洋洲。
     */
    OC = "OC",
    /** @South America
     * 南美洲。
     */
    SA = "SA",
    /** @Africa
     * 非洲。
     */
    AF = "AF",
    /** @south korea
     * 南韩。
     */
    KR = "KR",
    /** @us
     * 美国。
     */
    US = "US",
    /** @oversea
     * 海外。
     */
    OVS = "OVS"
}
/** @zh-cn
 * Agora RTM 服务的限定区域。设置限定区域之后，Agora RTM SDK 只能连接位于限定区域的 Agora RTM 服务。
 */
/**
 * Region for the Agora RTM service. After setting a region, the Agora RTM SDK can only connect to the Agora RTM service in the specified region.
 */
declare enum AreaCode {
    /** @zh-cn
     * （默认）全球。
     */
    /**
     * (Default) Global.
     */
    GLOBAL = "GLOBAL",
    /** @zh-cn
     * 印度。
     */
    /**
     * India.
     */
    INDIA = "INDIA",
    /** @zh-cn
     * 日本。
     */
    /**
     * Japan.
     */
    JAPAN = "JAPAN",
    /** @zh-cn
     * 除中国大陆以外的亚洲区域。
     */
    /**
     * Asia excluding mainland China.
     */
    ASIA = "ASIA",
    /** @zh-cn
     * 欧洲区域。
     */
    /**
     * Europe.
     */
    EUROPE = "EUROPE",
    /** @zh-cn
     * 中国大陆。
     */
    /**
     * Mainland China.
     */
    CHINA = "CHINA",
    /**
     * 北美区域。
     */
    /**
     * North America.
     */
    NORTH_AMERICA = "NORTH_AMERICA"
}
type EncryptionMode = 'NONE' | 'AES_128_GCM' | 'AES_256_GCM';
type StorageType = 'NONE' | 'USER' | 'CHANNEL';
type PresenceEventType = 
/**
 * 0: The presence none of this channel
 */
'NONE'
/**
 * 1: The presence snapshot of this channel
 */
 | 'SNAPSHOT'
/**
 * 2: The presence event triggered in interval mode
 */
 | 'INTERVAL'
/**
 * 3: Triggered when remote user join channel
 */
 | 'REMOTE_JOIN'
/**
 * 4: Triggered when remote user leave channel
 */
 | 'REMOTE_LEAVE'
/**
 * 5: Triggered when remote user's connection timeout
 */
 | 'REMOTE_TIMEOUT'
/**
 * 5: Triggered when user changed state
 */
 | 'REMOTE_STATE_CHANGED'
/**
 * 6: Triggered when user joined channel without presence service
 */
 | 'ERROR_OUT_OF_SERVICE';
type TopicEventType = 'NONE'
/**
 * REMOTE_JOIN_TOPIC: Triggered when remote user join a topic
 */
 | 'REMOTE_JOIN'
/**
 * REMOTE_LEAVE_TOPIC: Triggered when remote user leave a topic
 */
 | 'REMOTE_LEAVE'
/**
 * REMOTE_SNAPSHOT: The topic snapshot of this channel
 */
 | 'SNAPSHOT';
type StorageEventType = 'NONE' | 'SET' | 'SNAPSHOT' | 'REMOVE' | 'UPDATE';
type LockEventType = 'NONE' | 'SET' | 'REMOVED' | 'ACQUIRED' | 'RELEASED' | 'SNAPSHOT' | 'EXPIRED';
type TokenEventType = 'WILL_EXPIRE' | 'READ_PERMISSION_REVOKED';
declare enum LinkStateChangeReason4Report {
    /** * Unknown reason. */ UNKNOWN = 0,
    /** * Login. */ LOGIN = 1,
    /** * Login success. */ LOGIN_SUCCESS = 2,
    /** * Login timeout. */ LOGIN_TIMEOUT = 3,
    /** * Login not authorized. */ LOGIN_NOT_AUTHORIZED = 4,
    /** * Login rejected. */ LOGIN_REJECTED = 5,
    /** * Re-login. */ RELOGIN = 6,
    /** * Logout. */ LOGOUT = 7,
    /** * Auto reconnect. */ AUTO_RECONNECT = 8,
    /** * Reconnect timeout. */ RECONNECT_TIMEOUT = 9,
    /** * Reconnect success. */ RECONNECT_SUCCESS = 10,
    /** * Join. */ JOIN = 11,
    /** * Join success. */ JOIN_SUCCESS = 12,
    /** * Join failed. */ JOIN_FAILED = 13,
    /** * Rejoin. */ REJOIN = 14,
    /** * Leave. */ LEAVE = 15,
    /** * Invalid token. */ INVALID_TOKEN = 16,
    /** * Token expired. */ TOKEN_EXPIRED = 17,
    /** * Inconsistent app ID. */ INCONSISTENT_APP_ID = 18,
    /** * Invalid channel name. */ INVALID_CHANNEL_NAME = 19,
    /** * Invalid user ID. */ INVALID_USER_ID = 20,
    /** * Not initialized. */ NOT_INITIALIZED = 21,
    /** * Rtm service not connected. */ RTM_SERVICE_NOT_CONNECTED = 22,
    /** * Channel instance exceed limitation. */ CHANNEL_INSTANCE_EXCEED_LIMITATION = 23,
    /** * Operation rate exceed limitation. */ OPERATION_RATE_EXCEED_LIMITATION = 24,
    /** * Channel in error state. */ CHANNEL_IN_ERROR_STATE = 25,
    /** * Presence not connected. */ PRESENCE_NOT_CONNECTED = 26,
    /** * Same UID login. */ SAME_UID_LOGIN = 27,
    /** * Kicked out by server. */ KICKED_OUT_BY_SERVER = 28,
    /** * Keep alive timeout. */ KEEP_ALIVE_TIMEOUT = 29,
    /** * Connection error. */ CONNECTION_ERROR = 30,
    /** * Presence not ready. */ PRESENCE_NOT_READY = 31,
    /** * Network change. */ NETWORK_CHANGE = 32,
    /** * Service not supported. */ SERVICE_NOT_SUPPORTED = 33,
    /** * Stream channel not available. */ STREAM_CHANNEL_NOT_AVAILABLE = 34,
    /** * storage not available. */ STORAGE_NOT_AVAILABLE = 35,
    /** * Lock not available. */ LOCK_NOT_AVAILABLE = 36,
    /** * login too frequent */ LOGIN_TOO_FREQUENT = 37
}
declare enum LinkStateChangeReasonDescription {
    UNKNOWN = "Unknown",
    LOGIN = "Perform login operation",
    LOGIN_SUCCESS = "Login success",
    LOGIN_TIMEOUT = "Login timeout",
    LOGIN_NOT_AUTHORIZED = "Login not authorized",
    LOGIN_REJECTED = "Login rejected",
    RELOGIN = "Perform login operation again",
    LOGOUT = "Logout success",
    AUTO_RECONNECT = "Reconnecting",
    RECONNECT_TIMEOUT = "Reconnect timeout",
    RECONNECT_SUCCESS = "Reconnect success",
    JOIN = "Perform join operation",
    JOIN_SUCCESS = "Join channel success",
    JOIN_FAILED = "Join channel failed",
    REJOIN = "Perform join operation again",
    LEAVE = "Leave channel success",
    INVALID_TOKEN = "Invalid token",
    TOKEN_EXPIRED = "Token expired",
    INCONSISTENT_APP_ID = "Inconsistent app ID",
    INVALID_CHANNEL_NAME = "Invalid channel name",
    INVALID_USER_ID = "Invalid user id",
    NOT_INITIALIZED = "Not initialized",
    RTM_SERVICE_NOT_CONNECTED = "RTM service not connected",
    CHANNEL_INSTANCE_EXCEED_LIMITATION = "Channel instance exceed limitation",
    OPERATION_RATE_EXCEED_LIMITATION = "Operation rate exceed limitation",
    CHANNEL_IN_ERROR_STATE = "Channel in error state",
    PRESENCE_NOT_CONNECTED = "Presence not connected",
    SAME_UID_LOGIN = "The same uid login on another device",
    KICKED_OUT_BY_SERVER = "Kicked out by server",
    KEEP_ALIVE_TIMEOUT = "Keep alive timeout",
    CONNECTION_ERROR = "Connection error",
    PRESENCE_NOT_READY = "Presence not ready",
    NETWORK_CHANGE = "Network change",
    SERVICE_NOT_SUPPORTED = "Service not supported",
    STREAM_CHANNEL_NOT_AVAILABLE = "Stream channel not available",
    STORAGE_NOT_AVAILABLE = "Storage service is not available",
    LOCK_NOT_AVAILABLE = "Lock service is not available",
    LOGIN_TOO_FREQUENT = "Login too frequent"
}
declare enum TokenEventReason {
    WILL_EXPIRE = "The token is about to expire",
    READ_PERMISSION_REVOKED = "The token read permission is revoked"
}
declare enum ChannelTypeEnum {
    MESSAGE = 1,
    STREAM = 2,
    USER = 3
}

type ConstantsType_AreaCode = AreaCode;
declare const ConstantsType_AreaCode: typeof AreaCode;
type ConstantsType_ChannelTypeEnum = ChannelTypeEnum;
declare const ConstantsType_ChannelTypeEnum: typeof ChannelTypeEnum;
type ConstantsType_EncryptionMode = EncryptionMode;
type ConstantsType_LegacyAreaCode = LegacyAreaCode;
declare const ConstantsType_LegacyAreaCode: typeof LegacyAreaCode;
type ConstantsType_LinkStateChangeReason4Report = LinkStateChangeReason4Report;
declare const ConstantsType_LinkStateChangeReason4Report: typeof LinkStateChangeReason4Report;
type ConstantsType_LinkStateChangeReasonDescription = LinkStateChangeReasonDescription;
declare const ConstantsType_LinkStateChangeReasonDescription: typeof LinkStateChangeReasonDescription;
type ConstantsType_LockEventType = LockEventType;
type ConstantsType_MessageType = MessageType;
declare const ConstantsType_MessageType: typeof MessageType;
type ConstantsType_PresenceEventType = PresenceEventType;
type ConstantsType_RTMConnectionChangeReason = RTMConnectionChangeReason;
type ConstantsType_RTMConnectionState = RTMConnectionState;
type ConstantsType_StorageEventType = StorageEventType;
type ConstantsType_StorageType = StorageType;
type ConstantsType_TokenEventReason = TokenEventReason;
declare const ConstantsType_TokenEventReason: typeof TokenEventReason;
type ConstantsType_TokenEventType = TokenEventType;
type ConstantsType_TopicEventType = TopicEventType;
declare namespace ConstantsType {
  export { ConstantsType_AreaCode as AreaCode, ConstantsType_ChannelTypeEnum as ChannelTypeEnum, ConstantsType_LegacyAreaCode as LegacyAreaCode, ConstantsType_LinkStateChangeReason4Report as LinkStateChangeReason4Report, ConstantsType_LinkStateChangeReasonDescription as LinkStateChangeReasonDescription, ConstantsType_MessageType as MessageType, ConstantsType_TokenEventReason as TokenEventReason };
  export type { ConstantsType_EncryptionMode as EncryptionMode, ConstantsType_LockEventType as LockEventType, ConstantsType_PresenceEventType as PresenceEventType, ConstantsType_RTMConnectionChangeReason as RTMConnectionChangeReason, ConstantsType_RTMConnectionState as RTMConnectionState, ConstantsType_StorageEventType as StorageEventType, ConstantsType_StorageType as StorageType, ConstantsType_TokenEventType as TokenEventType, ConstantsType_TopicEventType as TopicEventType };
}

declare function setArea({ areaCodes, excludedArea, }: {
    areaCodes: AreaCode[];
    excludedArea?: AreaCode;
}): void;

interface BaseResponse {
    timestamp: number;
}
/**@zh-cn
 * 频道类型。
 * - `STREAM`: STREAM CHANNEL 频道；
 * - `MESSAGE`: MESSAGE CHANNEL 频道；
 * - `USEr`: 私密频道。
 */
/**
 * Channel type.
 * - `STREAM`: STREAM CHANNEL;
 * - `MESSAGE`: MESSAGE CHANNEL;
 * - `USEr`: PRIVATE CHANNEL.
 */
type ChannelType = 'STREAM' | 'MESSAGE' | 'USER';
/**@zh-cn
 * 服务类型。
 * - `MESSAGE`: RTM 基础服务；
 * - `STREAM`: STREAM CHANNEL 服务。
 */
/**
 * Service type.
 * - `MESSAGE`: RTM basic service;
 * - `STREAM`: STREAM CHANNEL service.
 */
type ServiceType = 'MESSAGE' | 'STREAM';

interface ILogger {
    loggerId: number;
}
declare class EventBase<T = {}> extends EventEmitter {
    logError: IDebugger;
    invokeTracker: (formatter: any, ...args: any[]) => void;
    resultTracker: (formatter: any, ...args: any[]) => void;
    errorTracker: (formatter: any, ...args: any[]) => void;
    eventTracker: (formatter: any, ...args: any[]) => void;
    protected info: IDebugger;
    protected warn: IDebugger;
    protected log: (formatter: any, ...args: any[]) => void;
    protected genLogger: (prefix: string, customPrefix?: string) => (formatter: any, ...args: any[]) => void;
    protected loggerId: number;
    readonly logger: ILogger;
    readonly name: string;
    constructor(logger: ILogger, name: string, trackEmit?: boolean, banOriginEventListener?: boolean);
}

interface LockDetail {
    /**@zh-cn
     * 分布式锁名称。
     */
    /**
     * Distributed lock name.
     */
    lockName: string;
    /**@zh-cn
     * 分布式锁的占有者。
     */
    /**
     * The owner of the distributed lock.
     */
    owner: string;
    /**@zh-cn
     * 锁的过期时间。
     */
    /**
     * The expiration time of the lock.
     */
    ttl: number;
}
interface GetLockResponse extends BaseResponse {
    /**@zh-cn
     * 此频道包含的锁数量。
     */
    /**
     * The number of locks contained in the channel.
     */
    totalLocks: number;
    /**@zh-cn
     * 每把锁的信息。
     */
    /**
     * The infos of every lock. See {@link LockDetail}
     */
    lockDetails: LockDetail[];
    /**@zh-cn
     * 锁所在频道名称。
     */
    /**
     * The channel name where the lock is located.
     */
    channelName: string;
    /**@zh-cn
     * 锁所在频道类型。
     */
    /**
     * The channel type where the lock is located.
     */
    channelType: ChannelType;
}
interface LockOperationResponse extends BaseResponse {
    channelName: string;
    channelType: ChannelType;
    lockName: string;
}
interface SetLockResponse extends LockOperationResponse {
}
interface RemoveLockResponse extends LockOperationResponse {
}
interface RevokeLockResponse extends LockOperationResponse {
}
interface ReleaseLockResponse extends LockOperationResponse {
}
interface AcquireLockResponse extends LockOperationResponse {
}
interface SetLockOptions {
    ttl?: number;
}
interface AcquireLockOptions {
    retry?: boolean;
}
declare class RTMLock {
    /**@zh-cn
     * 设置指定频道的分布式锁。
     * @param options.ttl 可选的 ttl ，表示拥有这把锁的用户掉线后，为其保留多长时间。若超过此时间用户没能恢复链接，锁将会被释放。 默认值 10s。@default 10
     * 最小值 10 秒.(默认值)
     * 最大值 300 秒.
     */
    /**
     * Set a distributed lock for the specified channel.
     * @param channelName A channel that needs to be specified.
     * @param channelType ChannelType for this channel. See {@link ChannelType}
     * @param lockName The lockName you wants to operate.
     * @param options.ttl An optional ttl indicates how long to keep the lock after the user who owns the lock goes offline. If the user fails to restore the connection after this time, the lock will be released. It is set to `10` by default. @default 10
     * Min 10 seconds.(default)
     * 300 seconds Maximum.
     */
    setLock(channelName: string, channelType: ChannelType, lockName: string, options?: SetLockOptions): Promise<SetLockResponse>;
    /**@zh-cn
     * 删除指定频道的分布式锁。
     */
    /**
     * Delete a distributed lock for the specified channel.
     * @param channelName A channel that needs to be specified.
     * @param channelType ChannelType for this channel. See {@link ChannelType}
     * @param lockName The lockName you wants to operate.
     */
    removeLock(channelName: string, channelType: ChannelType, lockName: string): Promise<RemoveLockResponse>;
    /**@zh-cn
     * 获取指定频道的分布式锁。
     * @param options.retry 可选的 retry ，当获取的锁被占用时是否继续尝试，直到成功获取或退出频道为止。 默认值 false。@default false
     */
    /**
     * Set a distributed lock for the specified channel.
     * @param channelName A channel that needs to be specified.
     * @param channelType ChannelType for this channel. See {@link ChannelType}
     * @param lockName The lockName you wants to operate.
     * @param options.retry An Optional retry , whether to keep trying when the acquired lock is occupied, until it is successfully acquired or the channel is exited. It is set to `false` by default. @default false
     */
    acquireLock(channelName: string, channelType: ChannelType, lockName: string, options?: AcquireLockOptions): Promise<AcquireLockResponse>;
    /**@zh-cn
     * 释放指定频道的分布式锁。
     */
    /**
     * Release a distributed lock for the specified channel.
     * @param channelName A channel that needs to be specified.
     * @param channelType ChannelType for this channel. See {@link ChannelType}
     * @param lockName The lockName you wants to operate.
     */
    releaseLock(channelName: string, channelType: ChannelType, lockName: string): Promise<ReleaseLockResponse>;
    /**@zh-cn
     * 剥夺指定频道的某个用户的分布式锁。
     */
    /**
     * Revoke a distributed lock of a user for the specified channel.
     * @param channelName A channel that needs to be specified.
     * @param channelType ChannelType for this channel. See {@link ChannelType}
     * @param lockName The lockName you wants to operate.
     * @param owner The owner of the lock you wants to revoke.
     */
    revokeLock(channelName: string, channelType: ChannelType, lockName: string, owner: string): Promise<RevokeLockResponse>;
    /**@zh-cn
     * 查询指定频道的分布式锁。
     */
    /**
     * Get all distributed locks for the specified channel.
     * @param channelName A channel that needs to be specified.
     * @param channelType ChannelType for this channel. See {@link ChannelType}
     */
    getLock(channelName: string, channelType: ChannelType): Promise<GetLockResponse>;
}

interface StateDetail {
    [key: string]: string;
}
interface OccupancyDetail {
    /**@zh-cn
     * 用户临时状态，目前仅支持 key，value 均为 string 类型的键值对。
     */
    /**
     * The temporary state of the user. Currently, only key-value pairs of string type are supported.
     */
    states: StateDetail;
    /**@zh-cn
     * 用户 ID。
     */
    userId: string;
    /**@zh-cn
     * 用户临时状态的数量。
     */
    /**
     * The number of temporary states of the user.
     */
    statesCount: number;
}
interface WhoNowResponse extends BaseResponse {
    /**@zh-cn
     * 当前频道内的用户总数。
     * @note 如果 whoNow 查询结果被分页，返回的结果中 totalOccupancy 为当前页的用户总数，不是整个频道的用户总数。
     */
    /**
     * The total number of users in the current channel.
     * @note If the result of whoNow is paginated, the totalOccupancy in the returned result is the total number of users on the current page, not the total number of users in the entire channel.
     */
    totalOccupancy: number;
    /**@zh-cn
     * 当前频道内的用户列表，详见 {@link OccupancyDetail}。
     */
    /**
     * The user list in the current channel. See {@link OccupancyDetail}.
     */
    occupants: OccupancyDetail[];
    /**@zh-cn
     * 下一页的页码，如果当前页是最后一页，返回的结果中 nextPage 为空字符串。
     * @note 当 nextPage 不为空字符串时，下次调用 whoNow 时，需要传入这个值，否则会返回相同的结果。
     */
    /**
     * The page number of the next page. If the current page is the last page, nextPage in the returned result is an empty string.
     * @note When nextPage is not an empty string, you need to pass in this value when calling whoNow next time, otherwise the same result will be returned.
     */
    nextPage: string;
}
interface GetOnlineUsersResponse extends WhoNowResponse {
}
interface WhoNowOptions {
    /**@zh-cn
     * 是否包含用户 ID，如果设置为 false，返回的结果中用户列表为空，默认为 `true`。
     */
    /**
     * Whether to include the user ID. If set as `false`, the user list in the returned result is empty. The default value is `true`.
     */
    includedUserId?: boolean;
    /**@zh-cn
     * 是否包含用户的临时状态，如果设置为 false，返回的结果中每个用户的 state 都为空对象，设置为 true 时，会携带每个用户设置的 state，默认为 `false`。
     */
    /**
     * Whether to include the user's temporary state. If set as `false`, the state of each user in the returned result is an empty object. If set as `true`, the state set by each user is carried. The default value is `false`.
     */
    includedState?: boolean;
    /**@zh-cn
     * 每页返回指定的用户数量，这个值需要在声网控制台中设置，默认为 50。如果当前频道内的用户数量超过了这个值，返回结果中 nextPage 会得到一个值，用于获取下一页的数据。
     * @note 该参数仅在 includedUserId 为 true 时有效。
     * @note 当 {@link WhoNowResponse} 的 nextPage 的值不为空字符串时，下次调用 whoNow 时，需要传入这个值，否则会返回相同的结果。
     */
    /**
     * The number of users returned per page. This value needs to be set in the Agora Console and is set as 50 by default. If the number of users in the current channel exceeds this value, the value of nextPage in the returned result is obtained to get the data of the next page.
     * @note This parameter is valid only when includedUserId is set as `true`.
     * @note When the value of nextPage in {@link WhoNowResponse} is not an empty string, you need to pass in this value when calling whoNow next time, otherwise the same result will be returned.
     */
    page?: string;
}
interface GetOnlineUsersOptions extends WhoNowOptions {
}
interface ChannelDetail {
    channelName: string;
    channelType: ChannelType;
}
interface WhereNowResponse extends BaseResponse {
    /**@zh-cn
     * 用户加入的频道列表。
     */
    /**
     * The list of channels that the user has joined.
     */
    channels: ChannelDetail[];
    /**@zh-cn
     * 用户加入的频道数量。
     */
    /**
     * The number of channels that the user has joined.
     */
    totalChannel: number;
}
interface GetUserChannelsResponse extends WhereNowResponse {
}
interface SetStateResponse extends BaseResponse {
}
interface GetStateResponse extends OccupancyDetail, BaseResponse {
    /**@zh-cn
     * 用户临时状态的数量。
     */
    /**
     * The number of temporary states of the user.
     */
    statesCount: number;
    /**@zh-cn
     * 用户临时状态，目前仅支持 key，value 均为 string 类型的键值对。
     */
    /**
     * The temporary state of the user. Currently, only key-value pairs of string type are supported.
     */
    states: StateDetail;
    /**
     * The user ID.
     */
    userId: string;
}
interface RemoveStateResponse extends BaseResponse {
}
interface RemoveStateOptions {
    states?: string[];
}
declare class RTMPresence {
    /**@zh-cn
     * 查询指定频道当前有哪些用户，以及用户的临时状态。
     * @param channelName 指定频道名称。
     * @param channelType 指定频道类型。
     * @param options 查询选项，详见 {@link WhoNowOptions}。
     * @returns 对象 {@link WhoNowResponse}
     */
    /**
     * Query which users are currently in the specified channel and the temporary state of the users.
     * @param channelName The specified channel name.
     * @param channelType The specified channel type.
     * @param options Query options. See {@link WhoNowOptions}.
     * @returns The {@link WhoNowResponse} object.
     */
    whoNow(channelName: string, channelType: ChannelType, options?: WhoNowOptions): Promise<WhoNowResponse>;
    /**@zh-cn
     * 查询指定频道当前有哪些用户，以及用户的临时状态。
     * @param channelName 指定频道名称。
     * @param channelType 指定频道类型。
     * @param options 查询选项，详见 {@link GetOnlineUsersOptions}。
     * @returns 对象 {@link GetOnlineUsersResponse}
     */
    /**
     * Query which users are currently in the specified channel and the temporary state of the users.
     * @param channelName The specified channel name.
     * @param channelType The specified channel type.
     * @param options Query options. See {@link GetOnlineUsersOptions}.
     * @returns The {@link GetOnlineUsersResponse} object.
     */
    getOnlineUsers(channelName: string, channelType: ChannelType, options?: GetOnlineUsersOptions): Promise<GetOnlineUsersResponse>;
    /**@zh-cn
     * 查询指定用户加入了哪些频道。
     * @param userId 指定用户 ID。
     * @returns 对象 {@link WhereNowResponse}
     */
    /**
     * Query which channels the specified user has joined.
     * @param userId The specified user ID.
     * @returns The {@link WhereNowResponse} object.
     */
    whereNow(userId: string): Promise<WhereNowResponse>;
    /**@zh-cn
     * 查询指定用户加入了哪些频道。
     * @param userId 指定用户 ID。
     */
    /**
     * Query which channels the specified user has joined.
     * @param userId The specified user ID.
     * @returns The {@link GetUserChannelsResponse} object.
     */
    getUserChannels(userId: string): Promise<GetUserChannelsResponse>;
    /**@zh-cn
     * 设置用户在指定频道下的临时状态。
     * @param channelName 指定频道名称。
     * @param channelType 指定频道类型。
     * @param state 指定用户的临时状态，详见 {@link StateDetail}。
     */
    /**
     * Set the temporary state of the user in the specified channel.
     * @param channelName The specified channel name.
     * @param channelType The specified channel type.
     * @param state The temporary state of the user. See {@link StateDetail}.
     */
    setState(channelName: string, channelType: ChannelType, state: StateDetail): Promise<SetStateResponse>;
    /**@zh-cn
     * 查询指定用户在指定频道下的临时状态。
     * @param userId 指定用户 ID。
     * @param channelName 指定频道名称。
     * @param channelType 指定频道类型。
     * @returns 对象 {@link GetStateResponse}
     */
    /**
     * Query the temporary state of the specified user in the specified channel.
     * @param userId The specified user ID.
     * @param channelName The specified channel name.
     * @param channelType The specified channel type.
     * @returns The {@link GetStateResponse} object.
     */
    getState(userId: string, channelName: string, channelType: ChannelType): Promise<GetStateResponse>;
    /**@zh-cn
     * 删除指定用户在指定频道下的临时状态。
     * @param channelName 指定频道名称。
     * @param channelType 指定频道类型。
     * @param options.states 传入要删除的 state key 列表, 不传代表全部删除。
     */
    /**
     * Delete the temporary state of the specified user in the specified channel.
     * @param channelName The specified channel name.
     * @param channelType The specified channel type.
     * @param options.states Pass in the list of state keys to be deleted, and all will be deleted if not passed in.
     */
    removeState(channelName: string, channelType: ChannelType, options?: RemoveStateOptions): Promise<RemoveStateResponse>;
}

/**@zh-cn
 * 元数据项的定义。
 */
/**
 * the define of metadata's item.
 */
interface MetadataItem {
    /**@zh-cn
     * 元数据项的名称。
     */
    /**
     * Name of metadata item.
     */
    key: string;
    /**@zh-cn
     * 元数据项的值。
     */
    /**
     * Value of metadata item.
     */
    value: string;
    /**@zh-cn
     * 元数据项的版本号。
     * -1 表示此属性可竞争读写最后更新者得，
     * 0 表示此属性只有在不存在时才创建，
     * 正整数表示只有版本号匹配时此属性才能被操作成功。
     */
    /**
     * Revision of metadata item. It is set to `-1` by default.
     * @default -1
     */
    revision?: number;
}
interface StorageData {
    /**@zh-cn
     * 此频道包含的属性组个数。
     */
    /**
     * The number of attribute groups contained in the channel.
     */
    totalCount: number;
    /**@zh-cn
     * 元数据的总版本号。
     */
    /**
     * The Revision of metadata.
     */
    majorRevision: number;
    /**@zh-cn
     * 元数据的信息。
     */
    /**
     * The infos of metadata.
     */
    metadata: Record<string, MetaDataDetail>;
}
interface ChannelMetadataOperationResponse extends BaseResponse {
    channelName: string;
    channelType: ChannelType;
}
interface UserMetadataOperationResponse extends BaseResponse {
    userId: string;
}
interface SetChannelMetadataResponse extends ChannelMetadataOperationResponse {
    /**@zh-cn
     * 此频道包含的属性组个数。
     */
    /**
     * The number of attribute groups contained in the channel.
     */
    totalCount: number;
}
interface SetUserMetadataResponse extends UserMetadataOperationResponse {
    /**@zh-cn
     * 此用户的属性组个数。
     */
    /**
     * The number of attribute groups of the user.
     */
    totalCount: number;
}
interface UpdateChannelMetadataResponse extends ChannelMetadataOperationResponse {
    /**@zh-cn
     * 此频道包含的属性组个数。
     */
    /**
     * The number of attribute groups contained in the channel.
     */
    totalCount: number;
}
interface UpdateUserMetadataResponse extends UserMetadataOperationResponse {
    /**@zh-cn
     * 此用户的属性组个数。
     */
    /**
     * The number of attribute groups of the user.
     */
    totalCount: number;
}
interface MetaDataDetail {
    /**@zh-cn
     * 元数据项的值。
     */
    /**
     * Value of metadata item.
     */
    value: string;
    /**@zh-cn
     * 元数据项的版本号。
     */
    /**
     * Revision of metadata item.
     */
    revision: number;
    /**@zh-cn
     * 元数据项最后一次被修改的时间戳。
     */
    /**
     * The timestamp when the metadata item was last modified.
     */
    updated: number;
    /**@zh-cn
     * 最后一次修改元数据项的用户。
     */
    /**
     * The user who last modified the metadata item.
     */
    authorUid: string;
}
interface GetChannelMetadataResponse extends StorageData, ChannelMetadataOperationResponse {
}
interface GetUserMetadataResponse extends StorageData, UserMetadataOperationResponse {
}
interface RemoveChannelMetadataResponse extends ChannelMetadataOperationResponse {
    /**@zh-cn
     * 此频道包含的属性组个数。
     */
    /**
     * The number of attribute groups contained in the channel.
     */
    totalCount: number;
}
interface RemoveUserMetadataResponse extends UserMetadataOperationResponse {
    /**@zh-cn
     * 此用户的属性组个数。
     */
    /**
     * The number of attribute groups of the user.
     */
    totalCount: number;
}
interface SubscribeUserMetaResponse extends UserMetadataOperationResponse {
}
interface UnsubscribeUserMetaResponse extends UserMetadataOperationResponse {
}
interface MetadataOptions {
    /**@zh-cn
     * 元数据的总版本号。
     * -1 表示此属性可竞争读写最后更新者得，
     * 0 表示此属性只有在不存在时才创建，
     * 正整数表示只有版本号匹配时此属性才能被操作成功。
     */
    /**
     * Revision of metadata. It is set to `1` by default.
     * @default -1
     */
    majorRevision?: number;
    /**@zh-cn
     * 分布式锁名称。如果设置，只有获得此锁的用户才有权限进行操作。
     */
    /**
     * Distributed lock name. If set, only the user who has acquired this lock will have permission to perform the operation. It is set to `''` by default.
     * @default ''
     */
    lockName?: string;
    /**@zh-cn
     * 本次操作是否在每个属性中添加服务器时间戳。
     */
    /**
     * Whether this operation adds server timestamp to each attribute. It is set to `false` by default.
     * @default false
     */
    addTimeStamp?: boolean;
    /**@zh-cn
     * 本次操作是否在每个属性中添加编辑者id。
     */
    /**
     * Whether to add editor id to each property in this operation. It is set to `false` by default.
     * @default false
     */
    addUserId?: boolean;
}
interface RemoveUserMetadataOptions extends MetadataOptions {
    /**
     * A user that needs to be specified. If you don't provide, this param default value is yourself.
     */
    userId?: string;
    /**
     * the items user wants to operate, each item must has unique key. If you don't provide this param, default clear all items. The item type please see {@link MetadataItem}.
     */
    data?: MetadataItem[];
}
interface RemoveChannelMetadataOptions extends MetadataOptions {
    /**
     * the items user wants to operate, each item must has unique key. If you don't provide this param, default clear all items. The item type please see {@link MetadataItem}.
     */
    data?: MetadataItem[];
}
interface SetOrUpdateUserMetadataOptions extends MetadataOptions {
    /**
     * A user that needs to be specified. If you don't provide, this param default value is yourself.
     */
    userId?: string;
}
interface GetUserMetadataOptions {
    userId?: string;
}
declare class RTMStorage {
    /**@zh-cn
     * 设置频道的元数据项。
     *
     */
    /**
     * set the metadata of a specific channel.
     *
     * @param channelName A channel that needs to be specified.
     * @param channelType channelType for this channel. See {@link ChannelType}
     * @param data the items user wants to operate, each item must has unique key. The item type please see {@link MetadataItem}.
     * @param options Options for this metadata operation. See {@link MetadataOptions}.
     */
    setChannelMetadata(channelName: string, channelType: ChannelType, data: MetadataItem[], options?: MetadataOptions): Promise<SetChannelMetadataResponse>;
    /**@zh-cn
     * 获取指定频道的元数据项。
     *
     */
    /**
     * get all metadata items of the channel.
     *
     * @param channelName A channel that needs to be specified.
     * @param channelType channelType for this channel. See {@link ChannelType}
     */
    getChannelMetadata(channelName: string, channelType: ChannelType): Promise<GetChannelMetadataResponse>;
    /**@zh-cn
     * 删除频道的元数据项。
     *
     */
    /**
     * delete metadata items of the channel.
     *
     * @param channelName A channel that needs to be specified.
     * @param channelType channelType for this channel. See {@link ChannelType}
     * @param options Options for this metadata operation. See {@link RemoveChannelMetadataOptions}.
     */
    removeChannelMetadata(channelName: string, channelType: ChannelType, options?: RemoveChannelMetadataOptions): Promise<RemoveChannelMetadataResponse>;
    /**@zh-cn
     * 更新指定频道的元数据项。
     *
     */
    /**
     * Update metadata items of the channel.
     *
     * @param channelName A channel that needs to be specified.
     * @param channelType channelType for this channel. See {@link ChannelType}
     * @param data the items user wants to operate, each item must has unique key. The item type please see {@link MetadataItem}.
     * @param options Options for this metadata operation. See {@link MetadataOptions}.
     */
    updateChannelMetadata(channelName: string, channelType: ChannelType, data: MetadataItem[], options?: MetadataOptions): Promise<UpdateChannelMetadataResponse>;
    /**@zh-cn
     * 设置指定用户的元数据项。如果用户之前没有属性，则自动创建用户属性。如果用户之前已有属性，将会根据需要设置的每组属性中"name"字段进行检索，如果原本用户属性中有"name"属性组则覆盖，如果没有则追加。
     *
     */
    /**
     * Set a specific user’s metadata. Automatically creates user attributes if the user has no attributes before. If the user has an attribute before, it will be retrieved according to the "name" field in each set of attributes that needs to be set. If there is a "name" attribute group in the original user attribute, it will be overwritten, and if not, it will be appended.
     *
     * @param data the items user wants to operate, each item must has unique key. The item type please see {@link MetadataItem}.
     * @param options Options for this metadata operation. See {@link SetOrUpdateUserMetadataOptions}.
     */
    setUserMetadata(data: MetadataItem[], options?: SetOrUpdateUserMetadataOptions): Promise<SetUserMetadataResponse>;
    /**@zh-cn
     * 获取指定用户的用户元数据项。
     *
     */
    /**
     * Get the user’s metadata of a specified user.
     * @param userId The userId of the user logging in the Agora RTM system.
     */
    getUserMetadata(options?: GetUserMetadataOptions): Promise<GetUserMetadataResponse>;
    /**@zh-cn
     * 删除指定用户的元数据项。
     *
     */
    /**
     * Delete a specific user’s metadata items.
     *
     * @param options Options for this metadata operation. See {@link RemoveUserMetadataOptions}.
     *
     */
    removeUserMetadata(options?: RemoveUserMetadataOptions): Promise<RemoveUserMetadataResponse>;
    /**@zh-cn
     * 更新指定用户的元数据项。
     *
     */
    /**
     * Update a specific user’s metadata items.
     *
     * @param data the items user wants to operate, each item must has unique key. The item type please see {@link MetadataItem}.
     * @param options Options for this metadata operation. See {@link SetOrUpdateUserMetadataOptions}.
     */
    updateUserMetadata(data: MetadataItem[], options?: SetOrUpdateUserMetadataOptions): Promise<UpdateUserMetadataResponse>;
    /**@zh-cn
     * 订阅特定用户的用户元数据更新事件。
     *
     */
    /**
     * Subscribe to user metadata update events for a specific users.
     * @param userId The userId of the user logging in the Agora RTM system.
     */
    subscribeUserMetadata(userId: string): Promise<SubscribeUserMetaResponse>;
    /**@zh-cn
     * 取消订阅特定用户的用户元数据更新事件。
     *
     */
    /**
     * Unsubscribe to user metadata update events for a specific users.
     * @param userId The userId of the user logging in the Agora RTM system.
     */
    unsubscribeUserMetadata(userId: string): Promise<UnsubscribeUserMetaResponse>;
}

declare namespace RTMEvents {
    type BaseEvent = {
        /**
         * Used for calibrating time
         * Sample Code:
         * ```javascript
         * const msOffset = timestamp - new Date().getTime(); // received every event need to calibrate time
         * const now = new Date().getTime() + msOffset; // Use the calibrated time as the current time
         * ```
         */
        timestamp: number;
    };
    interface PublishInfo {
        /**
         * The publisher user ID
         */
        publisherUserId: string;
        /**
         * The metadata of the publisher
         */
        publisherMeta: string;
    }
    interface topicDetail {
        /**
         * The name of the topic
         */
        topicName: string;
        /**
         * The publisher array
         */
        publishers: PublishInfo[];
        /**
         * The count of publisher in current topic
         */
        totalPublisher: number;
    }
    interface UserState {
        /**
         * The user id.
         */
        userId: string;
        /**
         * The user states.
         */
        states: StateDetail;
        statesCount: number;
    }
    interface UserList {
        /**
         * The list of users.
         */
        users: string[];
        /**
         * The number of users.
         */
        userCount: number;
    }
    interface IntervalDetail {
        /**
         * Joined users during this interval
         */
        join: UserList;
        /**
         * Left users during this interval
         */
        leave: UserList;
        /**
         * Timeout users during this interval
         */
        timeout: UserList;
        /**
         * The user state changed during this interval
         */
        userStateList: UserState[];
    }
    interface PresenceEvent extends BaseEvent {
        eventType: PresenceEventType;
        channelType: ChannelType;
        channelName: string;
        publisher: string;
        stateChanged: StateDetail;
        interval: IntervalDetail | null;
        snapshot: UserState[] | null;
    }
    interface StreamChannelConnectionStatusChangeEvent extends BaseEvent {
        channelName: string;
        state: ConnectionState;
        reason: ConnectionDisconnectedReason | string;
    }
    interface RTMConnectionStatusChangeEvent extends BaseEvent {
        state: RTMConnectionState;
        reason: RTMConnectionChangeReason;
    }
    interface MessageEvent extends BaseEvent {
        channelType: ChannelType;
        channelName: string;
        topicName: string;
        messageType: 'STRING' | 'BINARY';
        customType: string;
        message: string | Uint8Array;
        publisher: string;
        publishTime?: number;
    }
    interface StorageEvent extends BaseEvent {
        channelType: ChannelType;
        channelName: string;
        publisher: string;
        storageType: StorageType;
        eventType: StorageEventType;
        data: StorageData;
    }
    interface LockEvent extends BaseEvent {
        channelType: ChannelType;
        channelName: string;
        eventType: LockEventType;
        lockName: string;
        ttl: number;
        publisher: string;
        snapshot: LockDetail[];
        owner: string;
    }
    interface TopicEvent extends BaseEvent {
        /**
         * Indicate topic event type
         */
        eventType: TopicEventType;
        /**
         * The channel which the topic event was triggered
         */
        channelName: string;
        /**
         * The publisher which the topic event was triggered
         */
        publisher: string;
        /**
         * Topic information array.
         */
        topicInfos: topicDetail[];
        /**
         * The count of topicInfos.
         */
        totalTopics: number;
    }
    type LinkOperation = 'LOGIN' | 'LOGOUT' | 'JOIN' | 'LEAVE' | 'SERVER_REJECT' | 'AUTO_RECONNECT' | 'RECONNECTED' | 'HEARTBEAT_TIMEOUT' | 'SERVER_TIMEOUT' | 'NETWORK_CHANGE';
    type LinkState = 'IDLE' | 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'SUSPENDED' | 'FAILED';
    type LinkStateChangeReasonCode = 'UNKNOWN' | 'LOGIN' | 'LOGIN_SUCCESS' | 'LOGIN_TIMEOUT' | 'LOGIN_NOT_AUTHORIZED' | 'LOGIN_REJECTED' | 'RELOGIN' | 'LOGOUT' | 'AUTO_RECONNECT' | 'RECONNECT_TIMEOUT' | 'RECONNECT_SUCCESS' | 'JOIN' | 'JOIN_SUCCESS' | 'JOIN_FAILED' | 'REJOIN' | 'LEAVE' | 'INVALID_TOKEN' | 'TOKEN_EXPIRED' | 'INCONSISTENT_APP_ID' | 'INVALID_CHANNEL_NAME' | 'INVALID_USER_ID' | 'NOT_INITIALIZED' | 'RTM_SERVICE_NOT_CONNECTED' | 'CHANNEL_INSTANCE_EXCEED_LIMITATION' | 'OPERATION_RATE_EXCEED_LIMITATION' | 'CHANNEL_IN_ERROR_STATE' | 'PRESENCE_NOT_CONNECTED' | 'SAME_UID_LOGIN' | 'KICKED_OUT_BY_SERVER' | 'KEEP_ALIVE_TIMEOUT' | 'CONNECTION_ERROR' | 'PRESENCE_NOT_READY' | 'NETWORK_CHANGE' | 'SERVICE_NOT_SUPPORTED' | 'STREAM_CHANNEL_NOT_AVAILABLE' | 'STORAGE_NOT_AVAILABLE' | 'LOCK_NOT_AVAILABLE' | 'LOGIN_TOO_FREQUENT';
    interface LinkStateEvent extends BaseEvent {
        currentState: LinkState;
        previousState: LinkState;
        serviceType: ServiceType;
        operation: LinkOperation;
        reason: string;
        reasonCode: LinkStateChangeReasonCode;
        affectedChannels: string[];
        unrestoredChannels: string[];
        isResumed: boolean;
    }
    interface TokenEvent extends BaseEvent {
        eventType: TokenEventType;
        reason: string;
        affectedResources: {
            messageChannels: string[];
        };
    }
    interface RTMClientEventMap {
        /** @zh-cn
         * 通知 SDK 与 Agora RTM 系统的连接状态发生了改变。
         * @event
         * @param connectionStatus.newState 新的连接状态
         * @param connectionStatus.reason 状态改变的原因
         */
        /**
         * Occurs when the connection state changes between the SDK and the Agora RTM system.
         * @event
         * @param connectionStatus.newState The new connection state.
         * @param connectionStatus.reason Reasons for the connection state change.
         */
        status: (connectionStatus: RTMConnectionStatusChangeEvent | StreamChannelConnectionStatusChangeEvent) => void;
        presence: (presenceData: PresenceEvent) => void;
        message: (message: MessageEvent) => void;
        storage: (storageData: StorageEvent) => void;
        lock: (lockInfo: LockEvent) => void;
        topic: (topicEvent: TopicEvent) => void;
        /** @zh-cn
         *   当前使用的 RTM Token 登录权限还有 30 秒就会超过签发有效期。
         *
         * - 收到该回调时，请尽快在你的业务服务端生成新的 Token 并调用 {@link RTMClient.renewToken} 方法把新的 Token 传给 Token 验证服务器。
         */
        /**
         * The currently used RTM Token login permission will expire after 30 seconds.
         *
         * - When receiving this callback, generate a new RTM Token on the server and call the {@link RTMClient.renewToken} method to pass the new Token on to the server.
         */
        tokenPrivilegeWillExpire: (channelName: string) => void;
        linkState: (linkState: LinkStateEvent) => void;
        token: (tokenEvent: TokenEvent) => void;
    }
}

/**
 *  The option to get history message.
 */
interface GetHistoryMessageOptions {
    /**
     * The maximum count of messages to get.
     */
    messageCount?: number;
    /**
     * The start timestamp of this query range.
     */
    start?: number;
    /**
     * The end timestamp of the query range.
     */
    end?: number;
}
interface HistoryMessage {
    /**
     * The payload
     */
    message: string | Uint8Array;
    /**
     * Message type
     */
    messageType: 'STRING' | 'BINARY';
    /**
     * The custom type of the message
     */
    customType: string;
    /**
     * The publisher
     */
    publisher: string;
    /**
     * Timestamp of the message received by rtm server
     */
    timestamp: number;
}
/**@zh-cn
 * 历史消息频道类型。
 * - `MESSAGE`: MESSAGE CHANNEL 频道；
 * - `USEr`: 私密频道。
 */
/**
 * History Channel type.
 * - `MESSAGE`: MESSAGE CHANNEL;
 * - `USEr`: PRIVATE CHANNEL.
 */
type HistoryChannelType = Exclude<ChannelType, 'STREAM'>;
interface GetMessagesResponse extends BaseResponse {
    /**
     *  The history message list.
     */
    messageList: HistoryMessage[];
    /**
     * The message count.
     */
    count: number;
    /**
     * The timestamp of next history message. If newStart is 0, means there are no more history messages
     */
    newStart: number;
}
declare class RTMHistory {
    /**
     * Get history message of the channel.
     *
     * @param channelName A channel that needs to be specified.
     * @param HistoryChannelType channelType for this channel. See {@link HistoryChannelType}
     * @param options Options for this metadata operation. See {@link GetHistoryMessageOptions}.
     */
    getMessages(channelName: string, channelType: HistoryChannelType, options?: GetHistoryMessageOptions): Promise<GetMessagesResponse>;
}

interface StreamChannelOperationResponse extends BaseResponse {
    topicName: string;
}
interface JoinChannelResponse extends BaseResponse {
}
interface LeaveChannelResponse extends JoinChannelResponse {
}
interface JoinTopicResponse extends StreamChannelOperationResponse {
}
interface LeaveTopicResponse extends JoinTopicResponse {
}
interface PublishTopicMessageResponse extends StreamChannelOperationResponse {
}
declare namespace RTMStreamChannelStatusCode {
    const enum SubscribeTopicErrorCode {
        NO_ERROR = 0,
        PARTIALLY_SUCCESSFUL = 1,
        ALL_FAILED = 2,
        UNKNOWN_ERROR = 3,
        INVALID_PARAMS = 4,
        REMOTE_USER_IS_NOT_PUBLISHED = 5,
        INVALID_REMOTE_USER = 6,
        TIMEOUT = 7,
        ALREADY_SUBSCRIBED_USER = 20001,
        SUB_USER_EXCEED_LIMITATION = 20003,
        NOT_SUBSCRIBED_USER = 20004
    }
}
interface SubscribedFailedReason extends StreamChannelOperationResponse {
    /**@zh-cn
     * 订阅/退订 topic 里的用户失败。
     */
    /**
     * Failed to subscribe/unsubscribe users in topic.
     */
    user: string;
    /**@zh-cn
     * 操作对应的错误码。
     */
    /**
     * Error code of the operation. See {@link RTMStreamChannelStatusCode.SubscribeTopicErrorCode}
     */
    errorCode?: RTMStreamChannelStatusCode.SubscribeTopicErrorCode;
    /**@zh-cn
     * 失败原因。
     */
    /**
     * The failure reason.
     */
    reason?: string;
}
interface SubscribeTopicResponse extends StreamChannelOperationResponse {
    /**@zh-cn
     * 订阅成功的用户列表。
     */
    /**
     * List of successfully subscribed users.
     */
    succeedUsers: string[];
    /**@zh-cn
     * 订阅失败的用户列表及错误码。
     */
    /**
     * List of users whose subscription failed and error codes. See {@link SubscribedFailedReason}
     */
    failedUsers: string[];
    failedDetails: SubscribedFailedReason[];
}
interface UnsubscribeTopicResponse extends BaseResponse {
}
interface GetSubscribedUserListResponse extends StreamChannelOperationResponse {
    /**@zh-cn
     * 已经订阅的用户列表。
     */
    /**
     * List of subscribed users.
     */
    subscribed: string[];
}
interface JoinOptions {
    token?: string;
    withPresence?: boolean;
    /**@zh-cn
     * 可选参数，是否隐身加入频道。默认值为 false
     */
    /**
     * Optional parameter, whether subscribe channel be quiet, The default value is false. @default false
     */
    beQuiet?: boolean;
    withMetadata?: boolean;
    withLock?: boolean;
}
interface joinTopicOptions {
    meta?: any;
}
interface PublishTopicMessageOptions {
    /**@zh-cn
     * 自定义消息负载结构
     */
    /**
     * type of message payload
     */
    customType?: string;
}
interface SubscribeTopicOptions {
    users?: string[];
}
interface UnsubscribeTopicOptions {
    users?: string[];
}
declare class RTMStreamChannel {
    /**@zh-cn
     * 加入此频道。
     * @param options.token 登入 rtc 的 token。若未开启 token 功能则需要设置为 null。
     * @param options.withLock 可选参数，是否同时订阅分布式锁更新事件。默认值为 false。
     * @param options.withMetadata 可选参数，是否同时订阅频道属性。 默认值为 false。
     * @param options.withPresence 可选参数，是否同时订阅频道出席事件。 默认值为 true。
     */
    /**
     * Join this channel.
     * @param options.token Login token of rtc. If the token function is not enabled, it needs to be set to null.
     * @param options.withLock Optional parameter, whether to subscribe to the distributed lock update event at the same time. The default value is false. @default false
     * @param options.withMetadata Optional parameter, whether to subscribe to channel properties at the same time. The default value is false. @default false
     * @param options.withPresence Optional parameter, whether to subscribe to channel presence event at the same time. The default value is true. @default true
     */
    join(options?: JoinOptions): Promise<JoinChannelResponse>;
    /**@zh-cn
     * 离开此频道
     */
    /**
     * Leave this channel.
     */
    leave(): Promise<LeaveChannelResponse>;
    /**@zh-cn
     * 加入指定 topic。
     * @param topicName 要加入的 topic 名称。
     */
    /**
     * Join a specific topic.
     * @param topicName The topic name to join.
     * @param options.meta @default ''
     */
    joinTopic(topicName: string, options?: joinTopicOptions): Promise<JoinTopicResponse>;
    /**@zh-cn
     * 在指定 topic 内发消息。
     * @param topicName 指定的 topic 名称。
     * @param message 要发送的消息，支持文本消息和二进制消息。
     */
    /**
     * Send a message in the specified topic.
     * @param topicName The specified topic name.
     * @param message The message to send, supports text messages and binary messages.
     */
    publishTopicMessage(topicName: string, message: string | Uint8Array, options?: PublishTopicMessageOptions): Promise<PublishTopicMessageResponse>;
    /**@zh-cn
     * 离开指定 topic 。
     */
    /**
     * Leave a specified topic.
     * @param topicName The topic name to leave.
     */
    leaveTopic(topicName: string): Promise<LeaveTopicResponse>;
    /**@zh-cn
     * 订阅指定 topic 内的用户。
     * @param options.users users 为空时，默认订阅这个 topic 所有 user，当列表超出 64 人，随机订阅 64 人。
     */
    /**
     * Subscribe users in the specified topic.
     * @param options.users When users is empty, all users of this topic will be subscribed by default. When the list exceeds 64 users, 64 users will be randomly subscribed.
     */
    subscribeTopic(topicName: string, options?: SubscribeTopicOptions): Promise<SubscribeTopicResponse>;
    /**@zh-cn
     * 退订指定 topic 内的用户。
     * @param options.users users 为空时，默认取消订阅这个 topic 所有 user。
     */
    /**
     * Unsubscribe users in the specified topic.
     * @param options.users When users is empty, all users of this topic will be unsubscribed by default.
     */
    unsubscribeTopic(topicName: string, options?: UnsubscribeTopicOptions): Promise<UnsubscribeTopicResponse>;
    /**@zh-cn
     * 获取订阅了频道内指定 topic 下的哪些用户 。
     */
    /**
     * Get which users under the specified topic in the channel are subscribed..
     * @param topicName The specified topic name.
     */
    getSubscribedUserList(topicName: string): GetSubscribedUserListResponse;
}

interface SubscribeOptions {
    /**@zh-cn
     * 可选参数，是否订阅频道消息。默认值为 true。
     */
    /**
     * Optional parameter, whether to subscribe to channel messages. The default value is true. @default true
     */
    withMessage?: boolean;
    /**@zh-cn
     * 可选参数，是否同时订阅频道出席事件。 默认值为 true
     */
    /**
     * Optional parameter, whether to subscribe to channel presence event at the same time. The default value is true. @default true
     */
    withPresence?: boolean;
    /**@zh-cn
     * 可选参数，是否隐身加入频道。默认值为 false
     */
    /**
     * Optional parameter, whether subscribe channel be quiet, The default value is false. @default false
     */
    beQuiet?: boolean;
    /**@zh-cn
     * 可选参数，是否同时订阅频道属性。 默认值为 false
     */
    /**
     * Optional parameter, whether to subscribe to channel properties at the same time. The default value is false. @default false
     */
    withMetadata?: boolean;
    /**@zh-cn
     * 可选参数，是否同时订阅分布式锁更新事件。默认值为 false
     */
    /**
     * Optional parameter, whether to subscribe to the distributed lock update event at the same time. The default value is false. @default false
     */
    withLock?: boolean;
}
interface PrivateConfig {
    /**@zh-cn
     * 支持的服务类型，详见 {@link ServiceType}。
     * @note 请不要随意修改该配置，否则可能导致 SDK 无法正常工作。
     * @example
     * ```javascript
     * // 支持使用 RTM 基础功能与 STREAM CHANNEL 功能
     * privateConfig.serviceType = ['MESSAGE', 'STREAM'];
     * // 仅支持使用 RTM 基础功能，创建 STREAM CHANNEL 会失败
     * privateConfig.serviceType = ['MESSAGE'];
     * // 仅支持使用 STREAM CHANNEL 功能，登录 RTM 会失败
     * privateConfig.serviceType = ['STREAM'];
     * ```
     */
    /**
     * Supported service types, see {@link ServiceType}.
     * @note Please do not modify this configuration at will, otherwise the SDK may not work properly.
     * @example
     * ```javascript
     * // Support using RTM basic functions and STREAM CHANNEL functions
     * privateConfig.serviceType = ['MESSAGE', 'STREAM'];
     * // Only support using RTM basic functions, creating STREAM CHANNEL will fail
     * privateConfig.serviceType = ['MESSAGE'];
     * // Only support using STREAM CHANNEL functions, login RTM will fail
     * privateConfig.serviceType = ['STREAM'];
     * ```
     */
    serviceType: ServiceType[];
    /**@zh-cn
     * 用于登录时分配 RTM 基础服务和 STREAM CHANNEL 服务的域名列表。
     * @note 配置的域名所在的机器需要能够分配 RTM 和 STREAM CHANNEL两种服务。
     */
    /**
     * The list of domains used to assign RTM basic services and STREAM CHANNEL services when logging in.
     * @note The machine where the configured domain is located needs to be able to assign two services: RTM and STREAM CHANNEL.
     */
    accessPointHosts: string[];
    /**@zh-cn
     * 使用 SDK 期间产生的事件上传的主机列表。
     */
    /**
     * The list of hosts to which events generated during the use of the SDK are uploaded.
     */
    eventUploadHosts?: string[];
    /**@zh-cn
     * 使用 SDK 期间产生的日志上传的主机列表。
     */
    /**
     * The list of hosts to which logs generated during the use of the SDK are uploaded.
     */
    logUploadHosts?: string[];
    /**@zh-cn
     * 连接 RTM 基础服务时使用的后缀域名列表。
     * @note 请求 {@link accessPointHosts} 时获取到的 RTM 基础服务的 ip 为 `xxx.xxx.xxx.xxx`，则使用 `xxx-xxx-xxx-xxx.{@link originDomains}` 连接 RTM 基础服务。
     */
    /**
     * The list of suffix domains used when connecting to RTM basic services.
     * @note If the IP of the RTM basic service obtained when requesting {@link accessPointHosts} is `xxx.xxx.xxx.xxx`, use `xxx-xxx-xxx-xxx.${originDomains}` to connect to the RTM basic service.
     */
    originDomains?: string[];
}
interface RTMConfig {
    /**@zh-cn
     * 可选参数，消息加密方式，若不设置或设置为 ConstantsType.EncryptionMode.NONE ，则表示不启用加密功能。
     */
    /**
     * Optional parameter, message encryption mode, if not set or set to ConstantsType.EncryptionMode.NONE , it means that the encryption function is not enabled. The default value is ConstantsType.EncryptionMode.NONE. @default ConstantsType.EncryptionMode.NONE See {@link ConstantsType.EncryptionMode}
     */
    encryptionMode?: EncryptionMode;
    /**@zh-cn
     * 可选参数，加密需要用到的 salt，必须为 32 字节的二进制数组。若启用了加密功能，此参数必须提供。
     */
    /**
     * Optional parameter, the salt required for encryption, must be a 32-byte binary array. If encryption is enabled, this parameter must be provided.
     */
    salt?: Uint8Array;
    /**@zh-cn
     * 可选参数，加解密需要用到的密钥。若启用了加密功能，此参数必须提供。
     */
    /**
     * Optional parameter, the key needed for encryption and decryption. If encryption is enabled, this parameter must be provided.
     */
    cipherKey?: string;
    /**@zh-cn
     * 可选参数，用户掉线超过这个时间后，服务器会通知远端此用户超时，并清空用户的临时状态。默认值为 300 秒。
     * @example
     * ```javascript
     * // 设置 presenceTimeout 为 20s
     * const rtm = new RTM('appId', 'userId', { presenceTimeout: 20 });
     * ```
     */
    /**
     * Optional parameter, when the user is offline for more than this time, the server will notify the remote end that the user has timed out and clear the user's temporary state. The default value is 300 seconds. @default 300
     * @example
     * ```javascript
     * // Set presenceTimeout to 20s
     * const rtm = new RTM('appId', 'userId', { presenceTimeout: 20 });
     * ```
     */
    presenceTimeout?: number;
    /** @zh-cn
     * 是否上传日志。默认关闭。
     * - `true`: 启用日志上传；
     * - `false`: （默认）关闭日志上传。
     */
    /**
     * Whether to enable log upload. It is set to `false` by default.
     * - `true`: Enable log upload,
     * - `false`: (Default) Disable log upload.
     */
    logUpload?: boolean;
    /**@zh-cn
     * 是否使用代理。默认关闭。
     */
    /**
     * Whether to enable cloud proxy. It is set to `false` by default.
     */
    cloudProxy?: boolean;
    /**@zh-cn
     * 是否使用 string 类型的 uid，如果设置为 false，则会转化为 number 类型。
     * @default true
     * @note 当你使用过我司的 RTC 服务，uid 已经用过 int 类型，你希望配套使用 RTM 时，需要支持互通，可以将此配置设置为 false。
     */
    /**
     * Whether using string uid, if you set false, it translated to a number.
     * @default true
     * @note If you have used our RTC service and the uid has been used as int type, you want to use RTM, you need to support interoperability, you can set this configuration to false.
     */
    useStringUserId?: boolean;
    /** @zh-cn
     * 日志输出等级。
     *
     * 设置 SDK 的输出日志输出等级。不同的输出等级可以单独或组合使用。日志级别顺序依次为 NONE、ERROR、WARN、INFO 和 DEBUG。选择一个级别，你就可以看到在该级别之前所有级别的日志信息。例如，你选择 WARNING 级别，就可以看到在 ERROR 和 WARNING 级别上的所有日志信息。
     *
     */
    /**
     * Output log level of the SDK.
     *
     * You can use one or a combination of the filters. The log level follows the sequence of NONE, ERROR, WARN, INFO and DEBUG. Choose a level to see the logs preceding that level. If, for example, you set the log level to WARNING, you see the logs within levels ERROR and WARNING.
     *
     */
    logLevel?: 'debug' | 'info' | 'warn' | 'error' | 'none';
    /** @zh-cn
     * sdk 保活周期, 如果在配置时间内没有与后台通信, 那么认为用户掉线, 会进入自动重连, 单位 s, 取值范围 5-1800s
     * @default 5
     */
    /**
     * SDK keep-alive period, if there is no communication with the background within the configuration time, then the user is considered offline, will enter the automatic reconnection, unit s, value range 5-1800s
     * @default 5
     */
    heartbeatInterval?: number;
    /**
     * @zh-cn
     * 私有化部署配置，详见 {@link PrivateConfig}
     */
    /**
     * Private deployment configuration, see {@link PrivateConfig}
     */
    privateConfig?: PrivateConfig;
}
interface LoginOptions {
    /** @zh-cn
     * 登录 RTM 的 Token, 若您的项目开启了 App 证书，您必须要提供 Token 才能成功登录, 一般由您的服务端获取。
     */
    /**
     * The Token used to log in to the Agora RTM system. If your project has enabled App Certificate, you must provide a Token to log in successfully, generally obtained from your app server.
     */
    token?: string;
}
interface RTMOperationResponse extends BaseResponse {
    channelName: string;
}
interface SubscribeResponse extends RTMOperationResponse {
}
interface UnsubscribeResponse extends RTMOperationResponse {
}
interface LoginResponse extends BaseResponse {
}
interface LogoutResponse extends BaseResponse {
}
interface PublishResponse extends RTMOperationResponse {
}
interface RenewTokenResponse extends BaseResponse {
}
interface UpdateConfigResponse extends BaseResponse {
}
interface PublishOptions {
    /**@zh-cn
     * 自定义消息负载结构
     */
    /**
     * type of message payload
     */
    customType?: string;
    /**@zh-cn
     * 设置为 USER 则表示发送私密消息
     */
    /**
     * set to USER to send a private channel message
     */
    channelType?: ChannelType;
    /**@zh-cn
     * 设置为 true 则表示存储为历史消息
     */
    /**
     * Whether to store in history, true to enable
     */
    storeInHistory?: boolean;
}
interface RenewTokenOptions {
    /**@zh-cn
     * 需要更新 Token 的 STREAM CHANNEL 频道名
     * @note 当你收到 {@link RTMClientEventMap.tokenPrivilegeWillExpire} 事件且回调中包含 channelName 时，你需要传入此参数。
     */
    /**
     * The name of the STREAM CHANNEL channel that needs to update the Token
     * @note When you receive the {@link RTMClientEventMap.tokenPrivilegeWillExpire} event and the callback contains channelName, you need to pass in this parameter.
     */
    channelName?: string;
}
declare class RTMClient extends EventBase<RTMEvents.RTMClientEventMap> {
    constructor(
    /**@zh-cn
     * 传入项目的 App ID。必须是 ASCII 编码，长度为 32 个字符。
     */
    /**
     * Pass in the project's App ID. Must be ASCII encoded and 32 characters long.
     */
    appId: string, 
    /**@zh-cn
     * 登录 Agora RTM 系统的用户 ID。该字符串不可超过 64 字节。以下为支持的字符集范围:<ul>
     * <li>26 个小写英文字母 a-z</li>
     * <li>26 个大写英文字母 A-Z</li>
     * <li>10 个数字 0-9</li>
     * <li>空格</li>
     * <li>"!", "#", "$", "%", "&", "(", ")", "+", "-", ":", ";", "<", "=", ".", ">", "?", "@", "[", "]", "^", "_", " {", "}", "|", "~", ","</li>
     * </ul>
     * <p><b>Note</b></p><ul>
     * <li>请不要将 uid 设为空、null，或字符串 "null"。</li>
     * <li>uid 不支持 <code>number</code> 类型。建议调用 <code>toString()</code> 方法转化非 string 型 uid。</li>
     * </ul>
     */
    /**
     * The uid of the user logging in the Agora RTM system. The string length must be less than 64 bytes with the following character scope:<ul>
     * <li>All lowercase English letters: a to z</li>
     * <li>All uppercase English letters: A to Z</li>
     * <li>All numeric characters: 0 to 9</li>
     * <li>The space character.</li>
     * <li>Punctuation characters and other symbols, including: "!", "#", "$", "%", "&", "(", ")", "+", "-", ":", ";", "<", "=", ".", ">", "?", "@", "[", "]", "^", "_", " {", "}", "|", "~", ","</li>
     * </ul>
     * <p><b>Note</b></p><ul>
     * <li>The uid cannot be empty, or set as null or "null".</li>
     * <li>We do not support uids of the <code>number</code> type and recommend using the <code>toString()</code> method to convert your non-string uid.</li>
     * </ul>
     */
    userId: string, 
    /**@zh-cn
     * 可选参数。
     */
    /**
     * Optional parameter. See {@link RTMConfig}
     */
    rtmConfig?: RTMConfig);
    presence: RTMPresence;
    history: RTMHistory;
    /**@zh-cn
     * storage 实例，用于操作频道或用户属性。
     */
    /**
     * storage instance for manipulating channel or user properties. See {@link RTMStorage}
     */
    storage: RTMStorage;
    /**@zh-cn
     * lock 实例，用于操作频道的分布式锁。
     */
    /**
     * lock instance, used to operate the channel's distributed lock. See {@link RTMLock}
     */
    lock: RTMLock;
    /** @zh-cn
     * 用户登录 Agora RTM 系统。
     * @param options 登录 RTM 系统的选项。
     * @param options.token 登录 RTM 的 Token, 若您的项目开启了 App 证书，您必须要提供 Token 才能成功登录, 一般由您的服务端获取。
     * @note 在 RTM 和 RTC 结合使用的场景下，Agora 推荐你错时进行登录 RTM 系统和加入 RTC 频道的操作。
     * @note 如果用户在不同的 RtmClient 实例中以相同用户 ID 登录，之前的登录将会失效，用户会被踢出之前加入的频道。
     * @return 该 Promise 会在登录成功后 resolve。
     */
    /**
     * Logs in to the Agora RTM system.
     * @param options Options for logging in to the Agora RTM system.
     * @param options.token The Token used to log in to the Agora RTM system. If your project has enabled App Certificate, you must provide a Token to log in successfully, generally obtained from your app server.
     * @note If you use the Agora RTM SDK together with the Agora RTC SDK, Agora recommends that you avoid logging in to the RTM system and joining the RTC channel at the same time.
     * @note If the user logs in with the same uid from a different instance, the user will be kicked out of your previous login and removed from previously joined channels.
     * @return The Promise resolves after the user logs in to the Agora RTM system successfully.
     */
    login(options?: LoginOptions): Promise<LoginResponse>;
    /** @zh-cn
     * 退出登录，退出后自动断开连接和销毁回调监听。
     * @return 该 Promise 会在登出成功并断开 WebSocket 连接后 resolve。
     */
    /**
     * Allows a user to log out of the Agora RTM system.
     *
     * After the user logs out of the Agora RTM system, the SDK disconnects from the Agora RTM system and destroys the corresponding event listener.
     * @return The Promises resolves after the user logs out of the Agora RTM system and disconnects from WebSocket.
     */
    logout(): Promise<LogoutResponse>;
    /** @zh-cn
     * 向指定频道发送消息，支持文本消息与二进制消息。
     * @param channelName 指定的频道名
     * @param message 要发送的消息内容
     * @param options 可选参数，支持自定义消息负载结构，支持私密频道消息
     */
    /**
     * Send a message to a specified channel, supporting text messages and binary messages.
     * * ```javascript
     * // send private channel message
     * await rtmClient.publish('target_uid', 'message you want to send.', { channelType: 'USER' });
     * // send public channel message
     * await rtmClient.publish('channel_name', 'message you want to send.');
     * ```
     * @param channelName Name of specific channel.
     * @param message Message you wants to send.
     * @param options Optional parameter, support custom message payload structure, support private channel message
     */
    publish(channelName: string, message: string | Uint8Array, options?: PublishOptions): Promise<PublishResponse>;
    /** @zh-cn
     * 调用该方法订阅指定频道，订阅频道成功后可收到该频道消息，频道属性更新，锁事件。
     *
     * 你最多可以订阅 100 个频道。
     * @return 该 Promise 会在订阅频道成功后 resolve。
     */
    /**
     * Call this method to subscribe to the specified channel. After successfully subscribing to the channel, you can receive the channel message, channel attribute update, and lock event.
     *
     * You can subscribe a maximum of 100 channels.
     * @return The Promise resolves after the user successfully subscribes the channel.
     */
    subscribe(channelName: string, options?: SubscribeOptions): Promise<SubscribeResponse>;
    /** @zh-cn
     * 调用该方法退订指定频道，包括退订频道属性，用户属性，锁更新事件。
     * @return 该 Promise 会在退订频道成功后 resolve。
     */
    /**
     * Adjust to use this method to unsubscribe from the specified channel, including unsubscribe channel attributes, user attributes, and lock update events.
     * @param channelName Name of a specific channel.
     * @return The Promise resolves after the user successfully unsubscribes the channel.
     */
    unsubscribe(channelName: string): Promise<UnsubscribeResponse>;
    /** @zh-cn
     * 该方法创建一个 {@link RTMStreamChannel} 实例。
     * @param channelName 频道名称。该字符串不可超过 64 字节。以下为支持的字符集范围:<ul>
     * <li>26 个小写英文字母 a-z</li>
     * <li>26 个大写英文字母 A-Z</li>
     * <li>10 个数字 0-9</li>
     * <li>空格</li>
     * <li>"!", "#", "$", "%", "&", "(", ")", "+", "-", ":", ";", "<", "=", ".", ">", "?", "@", "[", "]", "^", "_", " {", "}", "|", "~", ","</li>
     * </ul>
     * <p><b>Note:</b></p><ul>
     * <li>请不要将 channelName 设为空、null，或字符串 "null"。</li></ul>
     * @return 一个 {@link RTMStreamChannel} 实例。
     */
    /**
     * Creates an {@link channelName} instance.
     * @param channelName The unique channel name of the Agora RTM stream channel. The string length must be less than 64 bytes with the following character scope:<ul>
     * <li>All lowercase English letters: a to z</li>
     * <li>All uppercase English letters: A to Z</li>
     * <li>All numeric characters: 0 to 9</li>
     * <li>The space character.</li>
     * <li>Punctuation characters and other symbols, including: "!", "#", "$", "%", "&", "(", ")", "+", "-", ":", ";", "<", "=", ".", ">", "?", "@", "[", "]", "^", "_", " {", "}", "|", "~", ","</li>
     * </ul>
     * <p><b>Note:</b></p><ul>
     * <li>The channelName cannot be empty, null, or "null".</li></ul>
     * @return An {@link RTMStreamChannel} instance.
     */
    createStreamChannel(channelName: string): RTMStreamChannel;
    /** @zh-cn
     * 更新当前 Token。
     *
     * @param token 新的 Token。
     * @param options 可选参数，详见 {@link RenewTokenOptions}。
     */
    /**
     * Renews the token.
     *
     * @param token Your new Token.
     * @param options Optional parameter, see {@link RenewTokenOptions}.
     */
    renewToken(token: string, options?: RenewTokenOptions): Promise<RenewTokenResponse>;
    /** @zh-cn
     * 修改 `RtmClient` 实例配置。修改实时生效。
     *
     * @param config 设置 SDK 是否上传日志以及日志的输出等级。
     */
    /**
     * Modifies the `RtmClient` instance configuration. The changes take effect immediately.
     *
     * @param config Sets whether the SDK uploads logs, and sets the output level of logs.
     */
    updateConfig(config: Pick<RTMConfig, 'logLevel' | 'logUpload' | 'cloudProxy'>): Promise<UpdateConfigResponse>;
    /** @zh-cn
     * 在 RTM 实例上添加 `listener` 函数到名为 `eventName` 的事件。其他 `RTMClient` 实例上的事件方法请参考 [`EventEmitter` API 文档](https://nodejs.org/docs/latest/api/events.html#events_class_eventemitter)。
     * @param eventName RTM 客户端事件的名称。事件列表请参考 {@link RTMEvents.RTMClientEventMap} 中的属性名。
     * @param listener 事件的回调函数。
     */
    /**
     * Adds the `listener` function to the RTM instance for the event named `eventName`. See [the `EventEmitter` API documentation](https://nodejs.org/docs/latest/api/events.html#events_class_eventemitter) for other event methods on the `RTMClient` instance.
     * @param eventName The name of the RTM client event. See the property names in the {@link RTMEvents.RTMClientEventMap} for the list of events.
     * @param listener The callback function of the RTM client event.
     */
    addEventListener<EventName extends keyof RTMEvents.RTMClientEventMap>(eventName: EventName, listener: RTMEvents.RTMClientEventMap[EventName]): void;
    /**@zh-cn
     * 从 RTM 实例上移除 `listener` 函数从名为 `eventName` 的事件。其他 `RTMClient` 实例上的事件方法请参考 [`EventEmitter` API 文档](https://nodejs.org/docs/latest/api/events.html#events_class_eventemitter)。
     * @param eventName RTM 客户端事件的名称。事件列表请参考 {@link RTMEvents.RTMClientEventMap} 中的属性名。
     * @param listener 事件的回调函数。
     */
    /**
     * Removes the `listener` function from the RTM instance for the event named `eventName`. See [the `EventEmitter` API documentation](https://nodejs.org/docs/latest/api/events.html#events_class_eventemitter) for other event methods on the `RTMClient` instance.
     * @param eventName The name of the RTM client event. See the property names in the {@link RTMEvents.RTMClientEventMap} for the list of events.
     * @param listener The callback function of the RTM client event.
     */
    removeEventListener<EventName extends keyof RTMEvents.RTMClientEventMap>(eventName: EventName, listener: RTMEvents.RTMClientEventMap[EventName]): void;
}
interface ErrorInfo {
    error: boolean;
    reason: string;
    operation: string;
    errorCode: number;
}

interface IErrorInfo {
    code?: number;
    serverCode?: number;
    originalError?: any;
}
declare class RTMBaseError extends Error implements ErrorInfo {
    originalError?: Error;
    code?: number;
    serverCode?: number;
    error: boolean;
    reason: string;
    operation: string;
    errorCode: number;
    constructor(operation: string, args?: string | readonly [string, ...any[]], errorInfo?: IErrorInfo | string | number);
}

interface IAgoraRTM {
    /** @zh-cn
     * Agora RTM SDK 的编译信息。
     */
    /**
     * Compilation information of the Agora RTM SDK.
     * @example `AgoraRTM.BUILD`
     */
    BUILD: string;
    RTM: typeof RTMClient;
    /** @zh-cn
     * Agora RTM SDK 的版本号。
     */
    /**
     * Version of the Agora RTM SDK.
     * @example `AgoraRTM.VERSION`
     */
    VERSION: string;
    setArea(options: {
        areaCodes: AreaCode[];
        excludedArea?: AreaCode;
    }): void;
    constantsType: typeof ConstantsType;
}

declare class Presence extends EventBase implements RTMPresence {
    whoNow(channelName: string, channelType: ChannelType, options?: WhoNowOptions): Promise<WhoNowResponse>;
    getOnlineUsers(channelName: string, channelType: ChannelType, options?: GetOnlineUsersOptions): Promise<GetOnlineUsersResponse>;
    whereNow(userId: string): Promise<WhereNowResponse>;
    getUserChannels(userId: string): Promise<GetUserChannelsResponse>;
    setState(channelName: string, channelType: ChannelType, state: StateDetail): Promise<SetStateResponse>;
    getState(userId: string, channelName: string, channelType: ChannelType): Promise<GetStateResponse>;
    removeState(channelName: string, channelType: ChannelType, options?: RemoveStateOptions): Promise<RemoveStateResponse>;
}

declare class Lock extends EventBase implements RTMLock {
    setLock(channelName: string, channelType: ChannelType, lockName: string, options?: SetLockOptions): Promise<SetLockResponse>;
    removeLock(channelName: string, channelType: ChannelType, lockName: string): Promise<RemoveLockResponse>;
    acquireLock(channelName: string, channelType: ChannelType, lockName: string, options?: AcquireLockOptions): Promise<AcquireLockResponse>;
    releaseLock(channelName: string, channelType: ChannelType, lockName: string): Promise<ReleaseLockResponse>;
    revokeLock(channelName: string, channelType: ChannelType, lockName: string, owner: string): Promise<RevokeLockResponse>;
    getLock(channelName: string, channelType: ChannelType): Promise<GetLockResponse>;
}

declare class History extends EventBase implements RTMHistory {
    getMessages(channelName: string, channelType: HistoryChannelType, options?: GetHistoryMessageOptions): Promise<GetMessagesResponse>;
}

declare class RStorage extends EventBase implements RTMStorage {
    setChannelMetadata(channelName: string, channelType: ChannelType, data: MetadataItem[], options?: MetadataOptions): Promise<SetChannelMetadataResponse>;
    getChannelMetadata(channelName: string, channelType: ChannelType): Promise<GetChannelMetadataResponse>;
    removeChannelMetadata(channelName: string, channelType: ChannelType, options?: RemoveChannelMetadataOptions): Promise<RemoveChannelMetadataResponse>;
    updateChannelMetadata(channelName: string, channelType: ChannelType, data: MetadataItem[], options?: MetadataOptions): Promise<UpdateChannelMetadataResponse>;
    setUserMetadata(data: MetadataItem[], options?: SetOrUpdateUserMetadataOptions): Promise<SetUserMetadataResponse>;
    getUserMetadata(options?: GetUserMetadataOptions): Promise<GetUserMetadataResponse>;
    removeUserMetadata(options?: RemoveUserMetadataOptions): Promise<RemoveUserMetadataResponse>;
    updateUserMetadata(data: MetadataItem[], options?: SetOrUpdateUserMetadataOptions): Promise<UpdateUserMetadataResponse>;
    subscribeUserMetadata(userId: string): Promise<SubscribeUserMetaResponse>;
    unsubscribeUserMetadata(userId: string): Promise<UnsubscribeUserMetaResponse>;
}

declare class StreamChannel extends EventBase implements RTMStreamChannel {
    join(options?: JoinOptions): Promise<JoinChannelResponse>;
    renewStreamChannelToken(token: string): Promise<void>;
    leave(): Promise<LeaveChannelResponse>;
    joinTopic(topicName: string, options?: joinTopicOptions): Promise<JoinTopicResponse>;
    publishTopicMessage(topicName: string, message: string | Uint8Array, options?: PublishTopicMessageOptions): Promise<PublishTopicMessageResponse>;
    leaveTopic(topicName: string): Promise<LeaveTopicResponse>;
    subscribeTopic(topicName: string, options?: SubscribeTopicOptions): Promise<SubscribeTopicResponse>;
    unsubscribeTopic(topicName: string, options?: UnsubscribeTopicOptions): Promise<UnsubscribeTopicResponse>;
    getSubscribedUserList(topicName: string): GetSubscribedUserListResponse;
}

declare class RTM extends EventBase<RTMEvents.RTMClientEventMap> implements RTMClient {
    presence: Presence;
    storage: RStorage;
    lock: Lock;
    history: History;
    constructor(appId: string, userId: string, rtmConfig?: RTMConfig);
    renewToken(token: string, options?: RenewTokenOptions): Promise<RenewTokenResponse>;
    updateConfig(params: Pick<RTMConfig, 'cloudProxy' | 'logUpload' | 'logLevel'>): Promise<UpdateConfigResponse>;
    login(options?: {
        token?: string;
    }): Promise<LoginResponse>;
    logout(): Promise<LogoutResponse>;
    publish(channelName: string, message: string | Uint8Array, options?: PublishOptions): Promise<PublishResponse>;
    subscribe(channelName: string, options?: SubscribeOptions): Promise<SubscribeResponse>;
    unsubscribe(channelName: string): Promise<UnsubscribeResponse>;
    createStreamChannel(channelName: string): StreamChannel;
    addEventListener<EventName extends keyof RTMEvents.RTMClientEventMap>(eventName: EventName, listener: RTMEvents.RTMClientEventMap[EventName]): void;
    removeEventListener<EventName extends keyof RTMEvents.RTMClientEventMap>(eventName: EventName, listener: RTMEvents.RTMClientEventMap[EventName]): void;
}

declare const _default: {
    BUILD: string;
    VERSION: string;
    RTM: typeof RTM;
    getParameter: (key: any) => any;
    setArea: typeof setArea;
    setParameter: (key: any, value: any) => void;
    constantsType: typeof ConstantsType;
    RTMBaseError: typeof RTMBaseError;
};

export { ConstantsType, RTMBaseError, RTMClient, RTMEvents, RTMHistory, RTMLock, RTMPresence, RTMStorage, RTMStreamChannel, RTMStreamChannelStatusCode, _default as default };
export type { AcquireLockOptions, AcquireLockResponse, BaseResponse, ChannelDetail, ChannelMetadataOperationResponse, ChannelType, ErrorInfo, GetChannelMetadataResponse, GetHistoryMessageOptions, GetLockResponse, GetMessagesResponse, GetOnlineUsersOptions, GetOnlineUsersResponse, GetStateResponse, GetSubscribedUserListResponse, GetUserChannelsResponse, GetUserMetadataOptions, GetUserMetadataResponse, HistoryChannelType, HistoryMessage, IAgoraRTM, IErrorInfo, JoinChannelResponse, JoinOptions, JoinTopicResponse, LeaveChannelResponse, LeaveTopicResponse, LockDetail, LockOperationResponse, LoginResponse, LogoutResponse, MetaDataDetail, MetadataItem, MetadataOptions, OccupancyDetail, PrivateConfig, PublishOptions, PublishResponse, PublishTopicMessageOptions, PublishTopicMessageResponse, RTMConfig, RTMOperationResponse, ReleaseLockResponse, RemoveChannelMetadataOptions, RemoveChannelMetadataResponse, RemoveLockResponse, RemoveStateOptions, RemoveStateResponse, RemoveUserMetadataOptions, RemoveUserMetadataResponse, RenewTokenOptions, RenewTokenResponse, RevokeLockResponse, ServiceType, SetChannelMetadataResponse, SetLockOptions, SetLockResponse, SetOrUpdateUserMetadataOptions, SetStateResponse, SetUserMetadataResponse, StateDetail, StorageData, StreamChannelOperationResponse, SubscribeOptions, SubscribeResponse, SubscribeTopicOptions, SubscribeTopicResponse, SubscribeUserMetaResponse, SubscribedFailedReason, UnsubscribeResponse, UnsubscribeTopicOptions, UnsubscribeTopicResponse, UnsubscribeUserMetaResponse, UpdateChannelMetadataResponse, UpdateConfigResponse, UpdateUserMetadataResponse, UserMetadataOperationResponse, WhereNowResponse, WhoNowOptions, WhoNowResponse, joinTopicOptions };
