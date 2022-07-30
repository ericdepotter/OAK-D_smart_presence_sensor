import { ApiContext } from '../../App';
import L from 'leaflet';
import { Marker, Popup } from "react-leaflet";
import React, { useCallback, useContext, useMemo, useRef, useState } from "react";

const iconCamera = new L.Icon({
    iconUrl: 'img/camera.png',
    iconRetinaUrl: 'img/camera.png',
    iconAnchor: null,
    popupAnchor: [0, -30],
    shadowUrl: null,
    shadowSize: null,
    shadowAnchor: null,
    iconSize: [48, 48]
});

function Camera(props) {
    const api = useContext(ApiContext);
    const [draggable, setDraggable] = useState(false);
    const [position, setPosition] = useState(props.camera.position);
    const markerRef = useRef(null);

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
    
    const save = useCallback(() => {
        const marker = markerRef.current;
        if (marker != null) {
            props.camera.position = marker.getLatLng();

            fetch(api.endpoint_api + '/camera/' + props.camera.id, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(props.camera)
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