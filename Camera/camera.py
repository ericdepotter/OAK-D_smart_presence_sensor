
import base64
import blobconverter
import cv2
import depthai as dai
import socketio
import time


ID = 'camera_1'

## DepthAI ##

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
#xoutBoundingBoxDepthMapping = pipeline.create(dai.node.XLinkOut)
#xoutDepth = pipeline.create(dai.node.XLinkOut)

xoutImage.setStreamName('image')
xoutNN.setStreamName('detections')
#xoutBoundingBoxDepthMapping.setStreamName('boundingBoxDepthMapping')
#xoutDepth.setStreamName('depth')

# Properties

#monoLeft.setImageOrientation(dai.CameraImageOrientation.ROTATE_180_DEG) NO EFFECT
monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
monoLeft.setBoardSocket(dai.CameraBoardSocket.LEFT)
#monoRight.setImageOrientation(dai.CameraImageOrientation.ROTATE_180_DEG) NO EFFECT
monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
monoRight.setBoardSocket(dai.CameraBoardSocket.RIGHT)

# Rotate images 180 degrees
rr = dai.RotatedRect()
rr.center.x, rr.center.y = monoLeft.getResolutionWidth() // 2, monoLeft.getResolutionHeight() // 2
rr.size.height, rr.size.width = monoLeft.getResolutionHeight(), monoLeft.getResolutionWidth()
rr.angle = 180

manipRotateLeft = pipeline.create(dai.node.ImageManip)
manipRotateLeft.initialConfig.setCropRotatedRect(rr, False)
monoLeft.out.link(manipRotateLeft.inputImage)

manipRotateRight = pipeline.create(dai.node.ImageManip)
manipRotateRight.initialConfig.setCropRotatedRect(rr, False)
monoRight.out.link(manipRotateRight.inputImage)

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

spatialDetectionNetwork.setBlobPath(blobconverter.from_zoo(name='mobilenet-ssd', shaves=5))
spatialDetectionNetwork.setConfidenceThreshold(0.5)
spatialDetectionNetwork.input.setBlocking(False)
spatialDetectionNetwork.setBoundingBoxScaleFactor(0.25)
spatialDetectionNetwork.setDepthLowerThreshold(100)
spatialDetectionNetwork.setDepthUpperThreshold(5000)

# Linking
manipRotateLeft.out.link(stereo.left)
manipRotateRight.out.link(stereo.right)

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
#spatialDetectionNetwork.boundingBoxMapping.link(xoutBoundingBoxDepthMapping.input)

stereo.depth.link(spatialDetectionNetwork.inputDepth)
#spatialDetectionNetwork.passthroughDepth.link(xoutDepth.input)

## Websocket ##

sio = socketio.Client()

camera_stream_active = True

# @sio.event
# def connect():
#     sio.emit("camera-info", ID)

FPS_CAMERA = 5
FPS_DETECTIONS = 15

# Connect to device and start pipeline
if __name__ == '__main__':

    with dai.Device(pipeline) as device:
        # Output queues will be used to get the rgb frames and nn data from the outputs defined above
        previewQueue = device.getOutputQueue(name='image', maxSize=1, blocking=False)
        detectionNNQueue = device.getOutputQueue(name='detections', maxSize=1, blocking=False)
        #xoutBoundingBoxDepthMapping = device.getOutputQueue(name='boundingBoxDepthMapping', maxSize=1, blocking=False)
        #depthQueue = device.getOutputQueue(name='depth', maxSize=1, blocking=False)
        
        startTime = time.monotonic()
        counter = 0
        fps = 0

        time_start = time.monotonic()
        time_last_camera = time.monotonic()
        time_last_detection = time.monotonic()

        max_fps = max(FPS_CAMERA, FPS_DETECTIONS)

        while True:
            if not sio.connected:
                try:
                    sio.connect('http://192.168.2.156:5000')
                except:
                    time.sleep(5)
                    continue

            #if delay_between_frames is not None:
            #    await asyncio.sleep(delay_between_frames)  # add delay if CPU usage is too high
    
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
            detections_filtered = []

            for detection in detections:
                try:
                    label = labelMap[detection.label]
                except:
                    label = detection.label

                if label != 'person':
                    continue

                # Denormalize bounding box
                x1 = int(detection.xmin * width)
                x2 = int(detection.xmax * width)
                y1 = int(detection.ymin * height)
                y2 = int(detection.ymax * height)

                cv2.putText(frame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (255, 255, 255))
                cv2.putText(frame, '{:.2f}'.format(detection.confidence*100), (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (255, 255, 255))
                cv2.putText(frame, f'X: {int(detection.spatialCoordinates.x)} mm', (x1 + 10, y1 + 50), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (255, 255, 255))
                cv2.putText(frame, f'Y: {int(detection.spatialCoordinates.y)} mm', (x1 + 10, y1 + 65), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (255, 255, 255))
                cv2.putText(frame, f'Z: {int(detection.spatialCoordinates.z)} mm', (x1 + 10, y1 + 80), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (255, 255, 255))

                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), cv2.FONT_HERSHEY_SIMPLEX)

                detections_filtered.append(detection)

            message = {
                'id': ID
            }


            if len(detections_filtered) > 0 and (time.monotonic() - time_last_detection) > 1.0/FPS_DETECTIONS:
                message['detections'] = list(map(lambda det: {'x': det.spatialCoordinates.x, 'y': det.spatialCoordinates.y, 'z': det.spatialCoordinates.z}, detections_filtered))
                time_last_detection = time.monotonic()

            if camera_stream_active and (time.monotonic() - time_last_camera) > 1.0/FPS_CAMERA:
                # Resize to original size
                frame = cv2.resize(frame, (640, 400), interpolation=cv2.INTER_AREA)
                cv2.putText(frame, 'NN fps: {:.2f}'.format(fps), (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, (255,255,255))

                _, jpeg = cv2.imencode('.jpg', frame)
                #message['image'] = f"data:image/jpeg;base64, {base64.b64encode(jpeg.tobytes()).decode()}"
                #message['image'] = (b'--frame\r\n'
                #                    b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                message['image'] = jpeg.tobytes()

                time_last_camera = time.monotonic()

            if len(message.keys()) > 1:
                try:
                    sio.emit('camera-update', message)
                except Exception as e:
                    time.sleep(5)
                    continue

            # Limit processing to FPS
            time_elapsed = time.monotonic() - time_start
            time.sleep(max(1./max_fps - time_elapsed, 0))
            time_start = time.monotonic()
