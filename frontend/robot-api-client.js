/**
 * Robot API Client for Alicia-D Robot Control
 * Example frontend JavaScript code for communicating with the FastAPI backend
 */

class RobotAPIClient {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL;
    }

    /**
     * Make HTTP request to the API
     */
    async request(endpoint, method = 'GET', data = null) {
        const url = `${this.baseURL}${endpoint}`;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, options);
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.detail || 'API request failed');
            }
            
            return result;
        } catch (error) {
            console.error(`API request failed: ${method} ${endpoint}`, error);
            throw error;
        }
    }

    // Connection methods
    async connect(port = "", baudrate = 1000000) {
        return this.request('/api/robot/connect', 'POST', { port, baudrate });
    }

    async disconnect() {
        return this.request('/api/robot/disconnect', 'POST');
    }

    async getStatus() {
        return this.request('/api/robot/status');
    }

    // State methods
    async getRobotState(format = 'rad') {
        return this.request(`/api/robot/state?format=${format}`);
    }

    async getJoints(format = 'rad') {
        return this.request(`/api/robot/joints?format=${format}`);
    }

    async getPose() {
        return this.request('/api/robot/pose');
    }

    async getGripper(format = 'rad') {
        return this.request(`/api/robot/gripper?format=${format}`);
    }

    // Movement methods
    async moveJoints(targetJoints, options = {}) {
        const request = {
            target_joints: targetJoints,
            joint_format: options.format || 'rad',
            speed_factor: options.speed || 1.0,
            T_default: options.time || 4.0,
            n_steps_ref: options.steps || 200,
            visualize: options.visualize || false
        };
        return this.request('/api/robot/move/joints', 'POST', request);
    }

    async moveCartesian(waypoints, options = {}) {
        const request = {
            waypoints: waypoints,
            planner_name: options.planner || 'cartesian',
            move_time: options.time || 3.0,
            visualize: options.visualize || false,
            show_ori: options.showOrientation || false,
            reverse: options.reverse || false
        };
        return this.request('/api/robot/move/cartesian', 'POST', request);
    }

    async moveHome() {
        return this.request('/api/robot/move/home', 'POST');
    }

    // Gripper control
    async controlGripper(command = null, angle = null, format = 'deg') {
        const request = { wait_for_completion: true };
        
        if (command) {
            request.command = command; // 'open' or 'close'
        } else if (angle !== null) {
            if (format === 'deg') {
                request.angle_deg = angle;
            } else {
                request.angle_rad = angle;
            }
        }
        
        return this.request('/api/robot/gripper', 'POST', request);
    }

    // Torque control (teaching mode)
    async controlTorque(command) {
        return this.request('/api/robot/torque', 'POST', { command }); // 'on' or 'off'
    }

    // Calibration
    async calibrate() {
        return this.request('/api/robot/calibrate', 'POST');
    }

    // Health check
    async health() {
        return this.request('/health');
    }
}

// Example usage
const robotAPI = new RobotAPIClient();

// Example functions that a frontend could use
async function connectToRobot() {
    try {
        const result = await robotAPI.connect();
        console.log('Connection result:', result);
        return result.success;
    } catch (error) {
        console.error('Failed to connect:', error);
        return false;
    }
}

async function getCurrentState() {
    try {
        const state = await robotAPI.getRobotState('deg');
        console.log('Robot state:', state);
        return state;
    } catch (error) {
        console.error('Failed to get state:', error);
        return null;
    }
}

async function moveToPosition(joints) {
    try {
        const result = await robotAPI.moveJoints(joints, { format: 'deg', speed: 1.0 });
        console.log('Move result:', result);
        return result.success;
    } catch (error) {
        console.error('Failed to move:', error);
        return false;
    }
}

async function openGripper() {
    try {
        const result = await robotAPI.controlGripper('open');
        console.log('Gripper result:', result);
        return result.success;
    } catch (error) {
        console.error('Failed to control gripper:', error);
        return false;
    }
}

async function enableTeachingMode() {
    try {
        const result = await robotAPI.controlTorque('off');
        console.log('Teaching mode enabled:', result);
        return result.success;
    } catch (error) {
        console.error('Failed to enable teaching mode:', error);
        return false;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { RobotAPIClient };
}