import json
import math
import numpy as np
from re import A
from shapely.geometry import Point, Polygon
import threading
from flask import Flask, request
from flask_cors import CORS
from flask_socketio import SocketIO,  send, emit


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
CORS(app, resources={r'/api/*': {'origins': '*'}})
socketio = SocketIO(app, cors_allowed_origins='*')


img_height = 771
img_width = 952

length_height = 6690
length_width = 8380


zones = {
    'living': [[510, 0], [125, 0], [125, 445], [510, 445]],
    'couch': [[250, 5], [130, 5], [130, 375], [250, 375]]
}

def compute_absolute_coordinates(coordinates, cam_rotation):
    # Convert angles from degrees to radias for the cosine and sine functions
    [yaw, pitch, roll] = list(map(lambda angle: angle * math.pi/180, cam_rotation))

    # Rotate around the z-axis
    yawMatrix = np.matrix([
        [math.cos(yaw), -math.sin(yaw), 0],
        [math.sin(yaw), math.cos(yaw), 0],
        [0, 0, 1]
    ])

    # Rotate around the y-axis
    pitchMatrix = np.matrix([
        [math.cos(pitch), 0, math.sin(pitch)],
        [0, 1, 0],
        [-math.sin(pitch), 0, math.cos(pitch)]
    ])

    # Rotate around the x-axis
    rollMatrix = np.matrix([
        [1, 0, 0],
        [0, math.cos(roll), -math.sin(roll)],
        [0, math.sin(roll), math.cos(roll)]
    ])

    R = yawMatrix * pitchMatrix * rollMatrix

    # OAK coordinates are [z, x, y] for yaw, pitch and roll
    location = R * np.matrix([[coordinates['z']], [coordinates['x']], [coordinates['y']]])
    #location = R * np.matrix([[coordinates['x']], [coordinates['y']], [coordinates['z']]])
    location = location.tolist()
    return [x for xs in location for x in xs]


def compute_map_coordinates(coordinates, cam_position):
    x = round(cam_position[1] + coordinates[0] / length_width * img_width)
    y = round(cam_position[0] - coordinates[1] / length_height * img_height)

    return [x, y]



@app.route('/api/camera_config')
def get_camera_config():
    return json.dumps([{'position': cameras['camera_1']['position']}])

@app.route('/api/map_dimensions')
def get_map_dimensions():
    return {'width': img_width, 'height': img_height}

@app.route('/api/zones')
def get_zones():
    return zones

# @socketio.on('message')
# def handle_message(message):
#     send(message)

# @socketio.on('json')
# def handle_json(json):
#     send(json, json=True)

cameras = {
    'camera_1': {
        'position': [575, 152],
        # yaw, pitch, roll
        'rotation': [90, 0, 0]
    }
}

# @socketio.on('disconnect')
# def disconnect():
#     print("%s disconnected" % (request.namespace.socket.sessid))
#     cameras.remove(request.namespace)

# @socketio.on('camera-info')
# def handle_camera_info(camera_name):
#     cameras[camera_name]["socket"] = request.namespace

previous_person = []
previous_zone = {'living': 0, 'couch': 0}

@socketio.on('camera-update')
def handle_camera_update(message):
    print(message.keys())

    global previous_person
    global previous_zone

    camera = cameras[message['name']]

    if 'image' in message:
        socketio.emit('camera-stream', message['image'])

    if 'detections' in message:
        det_response = []
        zone_response = {'living': 0, 'couch': 0}

        for detection in message['detections']:
            coordinates = compute_absolute_coordinates(detection, camera['rotation'])
            coordinates = compute_map_coordinates(coordinates, camera['position'])

            det_response.append(coordinates)

            # Check if in zone
            # Zone poinst are in (y, x)
            point = Point(coordinates[1], coordinates[0])

            for zone, points in zones.items():
                poly = Polygon(points)

                if poly.contains(point):
                    zone_response[zone] += 1

        # Don't continuously send messages when there are no persons (one message is sufficient).
        if len(previous_person) > 0 or len(det_response) > 0:
            socketio.emit('person-stream', det_response)
            previous_person = det_response

        for key, value in zone_response.items():
            if value != previous_zone[key]:
                # Zone information has changed -> send update
                socketio.emit('zone-stream', zone_response)
                previous_zone = zone_response
                break


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0')
    #threading.Thread(target=lambda: socketio.run(app)).start()

    #print(compute_absolute_coordinates({'x': 1, 'y': 2, 'z': 3}, [45, 0, 0]))
