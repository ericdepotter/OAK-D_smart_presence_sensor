import { ApiContext } from '../../App';
import L from 'leaflet';
import { Marker } from "react-leaflet";
import React, { useContext, useState, useEffect } from "react";
import socketIOClient from "socket.io-client";

const iconPerson = new L.Icon({
    iconUrl: 'img/person.png',
    iconRetinaUrl: 'img/person.png',
    iconAnchor: null,
    popupAnchor: null,
    shadowUrl: null,
    shadowSize: null,
    shadowAnchor: null,
    iconSize: new L.Point(24, 24)
});

function PersonsDetected(props) {
  const api = useContext(ApiContext);
  const [persons, setPersons] = useState([]);

  useEffect(() => {
    const socket = socketIOClient(api.endpoint_ws);
    socket.on("person-stream", data => {
        setPersons(data);
    });

    // CLEAN UP THE EFFECT
    return () => socket.disconnect();
  }, []);

  return persons.map(
    (pos, idx) => (
        <Marker position={[pos[1], pos[0]]} icon={iconPerson} key={idx}/>
    )
  );
}

export default PersonsDetected;