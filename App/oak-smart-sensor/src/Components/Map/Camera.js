import { ApiContext } from '../../App';
import L from 'leaflet';
import 'leaflet-rotatedmarker';
import { Marker, Popup } from "react-leaflet";
import React, { useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

const iconCamera = new L.Icon({
    iconUrl: 'img/camera.png',
    iconRetinaUrl: 'img/camera.png',
    iconAnchor: [null],
    popupAnchor: [0, -30],
    shadowUrl: null,
    shadowSize: null,
    shadowAnchor: null,
    iconSize: [48, 48]
});

function Camera(props) {
    const api = useContext(ApiContext);
    const { camera } = props;

    const [draggable, setDraggable] = useState(false);
    const [position, setPosition] = useState(camera.position);
    const markerRef = useRef(null);
    
    useEffect(() => {
        const marker = markerRef.current;
        if (marker) {
            marker.setRotationAngle(camera.rotation[0]);
            marker.setRotationOrigin('5px 24px');
        }
    }, [camera]);

    const eventHandlers = useMemo(
        () => ({
            dragend() {
                const marker = markerRef.current;
                if (marker != null) {
                    setPosition(marker.getLatLng());
                }
            },
        }),
        [],
    );
    
    const startEditing = useCallback(() => {
        setDraggable(true);
    }, []);

    console.log(camera.rotation[0]);
    
    const save = useCallback(() => {
        const marker = markerRef.current;
        if (marker != null) {
            camera.position = marker.getLatLng();

            fetch(api.endpoint_api + '/camera/' + camera.id, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(camera)
            });
        }
        
        setDraggable(false);
    }, []);
  
    return (
        <Marker
            draggable={draggable}
            eventHandlers={eventHandlers}
            icon={iconCamera}
            position={position}
            ref={markerRef}>
            <Popup minWidth={90}>
                <span onClick={draggable ? save : startEditing}>
                    {draggable
                        ? 'Click to save'
                        : 'Click to start editing'}
                </span>
            </Popup>
        </Marker>
    );
}

export default Camera;