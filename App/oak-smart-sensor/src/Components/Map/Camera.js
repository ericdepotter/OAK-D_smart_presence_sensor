import { CameraContext } from '../../App';
import L from 'leaflet';
import 'leaflet-rotatedmarker';
import { Marker } from "react-leaflet";
import React, { useContext, useEffect, useRef, useState } from "react";
import { cloneDeep } from 'lodash';

const iconCamera = new L.Icon({
    iconUrl: 'img/camera.png',
    iconRetinaUrl: 'img/camera.png',
    iconAnchor: [null],
    popupAnchor: [0, -60],
    shadowUrl: null,
    shadowSize: null,
    shadowAnchor: null,
    iconSize: [70, 70]
});

const iconCameraSelected = new L.Icon({
    iconUrl: 'img/camera_selected.png',
    iconRetinaUrl: 'img/camera_selected.png',
    iconAnchor: [null],
    popupAnchor: [0, -60],
    shadowUrl: null,
    shadowSize: null,
    shadowAnchor: null,
    iconSize: [70, 70]
});

function Camera(props) {
    const { activeCameraContext, setActiveCameraContext } = useContext(CameraContext);
    const { camera, onPositionUpdate } = props;

    const isEditing = activeCameraContext != null && camera.id === activeCameraContext;
    const markerRef = useRef(null);
    
    useEffect(() => {
        const marker = markerRef.current;
        if (marker) {
            marker.setRotationAngle(camera.rotation[0]);
            marker.setRotationOrigin('13px 35px');
        }
    }, [camera]);

    const eventHandlers = {
        dragend() {
            const marker = markerRef.current;
            if (marker != null) {
                const markerPosition = marker.getLatLng();
                onPositionUpdate(camera.id, [markerPosition['lat'], markerPosition['lng']]);
            }
        },
        click() {
            isEditing ? stopEditing() : startEditing();
        }
    };
    
    const startEditing = () => {
        setActiveCameraContext(camera.id);
    };
    
    const stopEditing = () => {
        setActiveCameraContext(null);
    };
  
    return (
        <React.Fragment>
            <Marker
                draggable={isEditing}
                eventHandlers={eventHandlers}
                icon={isEditing ? iconCameraSelected : iconCamera}
                position={camera.position}
                ref={markerRef}>
            </Marker>
        </React.Fragment>
    );
}

export default Camera;