import { ApiContext } from '../../App';
import L from 'leaflet';
import { Marker } from "react-leaflet";
import React, { useContext, useState, useEffect } from "react";

const iconCamera = new L.Icon({
    iconUrl: 'img/camera.png',
    iconRetinaUrl: 'img/camera.png',
    iconAnchor: null,
    popupAnchor: null,
    shadowUrl: null,
    shadowSize: null,
    shadowAnchor: null,
    iconSize: new L.Point(48, 48)
});

function Cameras() {
  const api = useContext(ApiContext);
  const [cameras, setCameras] = useState([]);

  useEffect(() => {
    fetch(api.endpoint_api + '/camera_config').then(res => res.json()).then(data => {
        setCameras(data);
    });
  }, []);

  return cameras.map(
    (c, idx) => (
        <Marker position={c.position} icon={iconCamera} key={idx}/>
    )
  );
}

export default Cameras;