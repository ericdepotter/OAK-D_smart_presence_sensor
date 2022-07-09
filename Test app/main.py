import asyncio
import base64
from tokenize import cookie_re
import blobconverter
import cv2
import dash
import dash_leaflet as dl
import dash_leaflet.express as dlx
import depthai as dai
from dash import html
import json
import math
import numpy as np
import threading
import time

from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate
from dash_extensions import WebSocket
from dash_extensions.javascript import assign
from numpy import vectorize
from shapely.geometry import Point, Polygon
from quart import Quart, websocket

#### Depth AI ####

'''
Spatial detection network demo.
    Performs inference on grayscale camera and retrieves spatial location coordinates: x,y,z relative to the center of depth map.
'''
# MobilenetSSD label texts
labelMap = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow",
            "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]

syncNN = True

# Create pipeline
pipeline = dai.Pipeline()

# Define sources and outputs
spatialDetectionNetwork = pipeline.create(dai.node.MobileNetSpatialDetectionNetwork)
monoLeft = pipeline.create(dai.node.MonoCamera)
monoRight = pipeline.create(dai.node.MonoCamera)
stereo = pipeline.create(dai.node.StereoDepth)

xoutImage = pipeline.create(dai.node.XLinkOut)
xoutNN = pipeline.create(dai.node.XLinkOut)
xoutBoundingBoxDepthMapping = pipeline.create(dai.node.XLinkOut)
xoutDepth = pipeline.create(dai.node.XLinkOut)

xoutImage.setStreamName("image")
xoutNN.setStreamName("detections")
xoutBoundingBoxDepthMapping.setStreamName("boundingBoxDepthMapping")
xoutDepth.setStreamName("depth")

# Properties

monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
monoLeft.setBoardSocket(dai.CameraBoardSocket.LEFT)
monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
monoRight.setBoardSocket(dai.CameraBoardSocket.RIGHT)

# Setting node configs
stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
stereo.setRectifyEdgeFillColor(0) # Black, to better see the cutout
stereo.setLeftRightCheck(True) # Better handling for occlusions
stereo.setExtendedDisparity(False) # Closer-in minimum depth, disparity range is doubled
stereo.setSubpixel(True) # Better accuracy for longer distance, fractional disparity 32-levels
stereo.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_7x7)
# Align depth map to the perspective of RGB camera, on which inference is done
#stereo.setDepthAlign(dai.CameraBoardSocket.RGB)
stereo.setOutputSize(monoLeft.getResolutionWidth(), monoLeft.getResolutionHeight())

spatialDetectionNetwork.setBlobPath(blobconverter.from_zoo(name="mobilenet-ssd", shaves=8))
spatialDetectionNetwork.setConfidenceThreshold(0.5)
spatialDetectionNetwork.input.setBlocking(False)
spatialDetectionNetwork.setBoundingBoxScaleFactor(0.25)
spatialDetectionNetwork.setDepthLowerThreshold(100)
spatialDetectionNetwork.setDepthUpperThreshold(5000)

# Linking
monoLeft.out.link(stereo.left)
monoRight.out.link(stereo.right)

manip = pipeline.create(dai.node.ImageManip)
# Option 1: Don't keep aspect ratio to maximize FOV
# This works very good
manip.initialConfig.setKeepAspectRatio(False)
manip.initialConfig.setResize(300, 300)
# Option 2: Letterboxing
# Also works well, seems a tiny bit worse in couch
#manip.initialConfig.setResizeThumbnail(300, 300)

manip.initialConfig.setFrameType(dai.RawImgFrame.Type.RGB888p)
stereo.rectifiedRight.link(manip.inputImage)

manip.out.link(spatialDetectionNetwork.input)
if syncNN:
    spatialDetectionNetwork.passthrough.link(xoutImage.input)
else:
    stereo.rectifiedRight.link(xoutImage.input)

spatialDetectionNetwork.out.link(xoutNN.input)
spatialDetectionNetwork.boundingBoxMapping.link(xoutBoundingBoxDepthMapping.input)

stereo.depth.link(spatialDetectionNetwork.inputDepth)
spatialDetectionNetwork.passthroughDepth.link(xoutDepth.input)

#### Websocket for video stream ####

# Setup small Quart server for streaming via websocket.
server = Quart(__name__)
#delay_between_frames = 0.05  # add delay (in seconds) if CPU usage is too high
delay_between_frames = 0  # add delay (in seconds) if CPU usage is too high


img_height = 771
img_width = 952

length_height = 6690
length_width = 8380

zones = {
    'living': [[510, 0], [125, 0], [125, 445], [510, 445]],
    'couch': [[250, 5], [130, 5], [130, 375], [250, 375]]
}

cam_image_height = 48
cam_image_width = 48
person_image_height = 24
person_image_width = 24
cam_position = [575, 152]
# yaw, pitch, roll
cam_rotation = [0, 0, 0]


def compute_absolute_coordinates(coordinates):
    # TODO fix this
    [yaw, pitch, roll] = cam_rotation

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
    location = R * np.matrix([[coordinates.z], [coordinates.x], [coordinates.y]])
    location = location.tolist()
    return [round(x) for xs in location for x in xs]


def compute_map_coordinates(coordinates):
    x = round(cam_position[1] - coordinates[1] / length_width * img_width)
    y = round(cam_position[0] - coordinates[0] / length_height * img_height)

    return [x, y]

@server.websocket("/stream")
async def stream():
    # Connect to device and start pipeline
    with dai.Device(pipeline) as device:
        # Output queues will be used to get the rgb frames and nn data from the outputs defined above
        previewQueue = device.getOutputQueue(name="image", maxSize=4, blocking=False)
        detectionNNQueue = device.getOutputQueue(name="detections", maxSize=4, blocking=False)
        xoutBoundingBoxDepthMapping = device.getOutputQueue(name="boundingBoxDepthMapping", maxSize=4, blocking=False)
        depthQueue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)
        
        startTime = time.monotonic()
        counter = 0
        fps = 0

        while True:
            if delay_between_frames is not None:
                await asyncio.sleep(delay_between_frames)  # add delay if CPU usage is too high
    
            inPreview = previewQueue.get()
            inDet = detectionNNQueue.get()

            counter += 1
            current_time = time.monotonic()
            if (current_time - startTime) > 1 :
                fps = counter / (current_time - startTime)
                counter = 0
                startTime = current_time

            frame = inPreview.getCvFrame()

            # If the frame is available, draw bounding boxes on it and show the frame
            height = frame.shape[0]
            width  = frame.shape[1]

            detections = inDet.detections
            det_response = []
            zone_response = {'living': 0, 'couch': 0}
            for detection in detections:
                # Denormalize bounding box
                x1 = int(detection.xmin * width)
                x2 = int(detection.xmax * width)
                y1 = int(detection.ymin * height)
                y2 = int(detection.ymax * height)

                try:
                    label = labelMap[detection.label]
                except:
                    label = detection.label

                if label != "person":
                    continue

                cv2.putText(frame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (255, 255, 255))
                cv2.putText(frame, "{:.2f}".format(detection.confidence*100), (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (255, 255, 255))
                cv2.putText(frame, f"X: {int(detection.spatialCoordinates.x)} mm", (x1 + 10, y1 + 50), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (255, 255, 255))
                cv2.putText(frame, f"Y: {int(detection.spatialCoordinates.y)} mm", (x1 + 10, y1 + 65), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (255, 255, 255))
                cv2.putText(frame, f"Z: {int(detection.spatialCoordinates.z)} mm", (x1 + 10, y1 + 80), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (255, 255, 255))

                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), cv2.FONT_HERSHEY_SIMPLEX)

                coordinates = compute_absolute_coordinates(detection.spatialCoordinates)
                coordinates = compute_map_coordinates(coordinates)

                det_response.append(coordinates)

                # Check if in zone
                # Zone poinst are in (y, x)
                point = Point(coordinates[1], coordinates[0])

                for zone, points in zones.items():
                    poly = Polygon(points)

                    if poly.contains(point):
                        zone_response[zone] += 1

            cv2.putText(frame, "NN fps: {:.2f}".format(fps), (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, (255,255,255))

            _, jpeg = cv2.imencode('.jpg', frame)

            response = {
                'image': f"data:image/jpeg;base64, {base64.b64encode(jpeg.tobytes()).decode()}",
                'persons': det_response,
                'zones': zone_response
            }

            await websocket.send(json.dumps(response))




#### Dash app ####

MAP_ID = "map-id"
POLYLINE_ID = "polyline-id"
POLYGON_ID = "polygon-id"

dummy_pos = [0, 0]
dlatlon2 = 5  # Controls tolerance of closing click

app = dash.Dash()
# app.layout = html.Div([
#     dl.Map(id=MAP_ID, center=[57.671667, 11.980833], zoom=16, children=[
#         dl.TileLayer(),  # Map tiles, defaults to OSM
#         dl.Polyline(id=POLYLINE_ID, positions=[dummy_pos]),  # Create a polyline, cannot be empty at the moment
#         dl.Polygon(id=POLYGON_ID, positions=[dummy_pos]),  # Create a polygon, cannot be empty at the moment
#     ], style={'width': '1000px', 'height': '500px'}),
# ])

app.layout = html.Div([
    dl.Map(
        id=MAP_ID,
        center=[img_width/2, img_height/2],
        zoom=-8,
        children=[
            dl.ImageOverlay(
                url=app.get_asset_url('House plan (Edited).png'),
                bounds=[[0,0], [img_height,img_width]],
                className="no-transform"
            ),  # Background image
            # dl.Polyline(id=POLYLINE_ID, positions=[dummy_pos]),  # Create a polyline, cannot be empty at the moment
            # dl.Polygon(id=POLYGON_ID, positions=[dummy_pos]),  # Create a polygon, cannot be empty at the moment
            dl.Polygon(id='zone_living', positions=[zones['living']]),
            dl.Polygon(id='zone_couch', positions=[zones['couch']]),
            dl.ImageOverlay(
                id='camera',
                url=app.get_asset_url('camera.png'),
                bounds=[[cam_position[0] - 20, cam_position[1] - cam_image_width / 2], [cam_position[0] + cam_image_height - 20, cam_position[1] + cam_image_width / 2]],
                className='transform-center'
            ),
            dl.ImageOverlay(
                id='person',
                url=app.get_asset_url('person.png'),
                bounds=[[-100, -100], [-100, -100]],
                className='transform-center'
            ),
            dl.ImageOverlay(
                id='person-1',
                url=app.get_asset_url('person.png'),
                bounds=[[-100, -100], [-100, -100]],
                className='transform-center'
            ),
            dl.ImageOverlay(
                id='person-2',
                url=app.get_asset_url('person.png'),
                bounds=[[-100, -100], [-100, -100]],
                className='transform-center'
            )
        ], 
        style={'width': img_width, 'height': img_height, 'transform': None},
        crs="Simple",
        dragging=False,
        zoomControl=False,
        scrollWheelZoom=False,
        doubleClickZoom=False,
        boxZoom=False
    ),
    html.Div([
        html.Img(id='camera-stream', style={'width': 300, 'height': 300, 'padding': 10}),
        html.Div(id='zones', style={'width': '100%', 'padding': 50, 'text-align': 'center', 'font-size': '24pt'})
    ], id='container', style={'display': 'flex', 'flex-direction': 'column', 'align-items': 'center'}),
    html.Div(id='hidden-div', style={'display':'none'}),
    WebSocket(id='ws-camera', url=f'ws://127.0.0.1:5000/stream')
], style={'display': 'flex', 'padding': 48, 'justify-content': 'space-around'})

# Copy data from websocket to Img element.
app.clientside_callback(
    """
    function(m) {
        zonesTextDiv = document.getElementById('zones');
        zonesTextDiv.innerHTML = '';

        if (!m) {return '';}
        message = JSON.parse(m.data);

        console.log(message.zones);
        zonesTextDiv.innerHTML = `Living: ${message.zones.living}<br/>Couch: ${message.zones.couch}` 

        return message.image;
    }
    """,
    Output(f"camera-stream", "src"),
    Input(f"ws-camera", "message")
)
app.clientside_callback(
    """
    function(m) {
        if (!m) {return [[-100, -100], [-100, -100]];}
        message = JSON.parse(m.data);
        if (message.persons.length == 0) {
            return [[-100, -100], [-100, -100]];
        }

        var [x, y] = message.persons[0];
        return [[y - 12, x - 12], [y + 12, x + 12]];
    }
    """,
    Output(f"person", "bounds"),
    Input(f"ws-camera", "message")
)
app.clientside_callback(
    """
    function(m) {
        if (!m) {return [[-100, -100], [-100, -100]];}
        message = JSON.parse(m.data);
        if (message.persons.length <= 1) {
            return [[-100, -100], [-100, -100]];
        }

        var [x, y] = message.persons[1];
        return [[y - 12, x - 12], [y + 12, x + 12]];
    }
    """,
    Output(f"person-1", "bounds"),
    Input(f"ws-camera", "message")
)
app.clientside_callback(
    """
    function(m) {
        if (!m) {return [[-100, -100], [-100, -100]];}
        message = JSON.parse(m.data);
        if (message.persons.length <= 2) {
            return [[-100, -100], [-100, -100]];
        }

        var [x, y] = message.persons[2];
        return [[y - 12, x - 12], [y + 12, x + 12]];
    }
    """,
    Output(f"person-2", "bounds"),
    Input(f"ws-camera", "message")
)


# @app.callback([Output(POLYLINE_ID, "positions"), Output(POLYGON_ID, "positions")],
#               [Input(MAP_ID, "click_lat_lng")],
#               [State(POLYLINE_ID, "positions")])
# def update_polyline_and_polygon(click_lat_lng, positions):
#     if click_lat_lng is None or positions is None:
#         raise PreventUpdate()
#     # On first click, reset the polyline.
#     if len(positions) == 1 and positions[0] == dummy_pos:
#         return [click_lat_lng], [dummy_pos]
#     # If the click is close to the first point, close the polygon.
#     dist2 = (positions[0][0] - click_lat_lng[0]) ** 2 + (positions[0][1] - click_lat_lng[1]) ** 2
#     if dist2 < dlatlon2:
#         print(positions)
#         return [dummy_pos], positions
#     # Otherwise, append the click position.
#     positions.append(click_lat_lng)
#     return positions, [dummy_pos]

@app.callback([Output('hidden-div', "positions")],
              [Input(MAP_ID, "click_lat_lng")])
def update_polyline_and_polygon(click_lat_lng):
    print(click_lat_lng)
    return None


if __name__ == '__main__':
    #app.run_server(debug=True)
    threading.Thread(target=app.run_server).start()
    server.run()